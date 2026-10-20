# One SSH master per port: control sockets identify only tunnels owned here.
function __rafiki_forward_port --argument-names port
    string match -qr '^[0-9]{1,5}$' -- "$port"; or return 1
    set -l number (math "$port + 0")
    test "$number" -ge 1; and test "$number" -le 65535; or return 1
    echo "$number"
end

function __rafiki_forward_tracked --argument-names state_dir
    for socket in "$state_dir"/p*.sock
        set -l port (string match -rg '^p([0-9]{1,5})[.]sock$' -- (path basename "$socket"))
        __rafiki_forward_port "$port"
    end
end

function __rafiki_forward_running --argument-names state_dir target port
    set -l socket "$state_dir/p$port.sock"
    test -S "$socket"; and not test -L "$socket"; or return 1
    command ssh -S "$socket" -O check "$target" >/dev/null 2>&1
end

function __rafiki_forward_occupied --argument-names port
    command lsof -nP -a -iTCP:$port -sTCP:LISTEN -t >/dev/null 2>&1
end

function __rafiki_forward_status --argument-names state_dir target
    set -l ports 5432 8080 8000 27017 6379 $argv[3..] (__rafiki_forward_tracked "$state_dir")
    set -l active_ports
    set ports (printf '%s\n' $ports | command sort -nu)
    printf '\nStatus atual — %s → 127.0.0.1\n' "$target"
    printf '%-7s %-24s %s\n' Porta Estado Serviço
    for port in $ports
        set -l state inativa
        if __rafiki_forward_running "$state_dir" "$target" "$port"
            set state 'ativa (rafiki-forward)'
            set -a active_ports "$port"
        else if __rafiki_forward_occupied "$port"
            set state 'ocupada por outro processo'
        end
        set -l label ''
        switch "$port"
            case 5432
                set label PostgreSQL
            case 8080
                set label 'pgAdmin / Gateway'
            case 8000
                set label 'FastAPI / API'
            case 27017
                set label MongoDB
            case 6379
                set label Redis
        end
        printf '%-7s %-24s %s\n' "$port" "$state" "$label"
    end
    if test (count $active_ports) -gt 0
        printf '\nParar uma porta: rafiki-forward stop %s\n' "$active_ports[1]"
        if test (count $active_ports) -gt 1
            printf 'Parar estas portas: rafiki-forward stop %s\n' (string join ' ' $active_ports)
        end
    else
        printf '\nExemplo para uma porta: rafiki-forward stop 8080\n'
    end
    printf 'Parar todos os túneis gerenciados: rafiki-forward stop all\n'
end

# Called in a separate fish under lockf, so cancellation releases the OS lock.
function __rafiki_forward_change --argument-names state_dir target action port
    set -l socket "$state_dir/p$port.sock"
    if __rafiki_forward_running "$state_dir" "$target" "$port"
        if test "$action" = start
            echo "Já estava ativa: porta $port."
            return 0
        end
        if not command ssh -S "$socket" -O exit "$target" >/dev/null
            echo "Falha ao parar a porta $port." >&2
            return 1
        end
        for attempt in (seq 1 20)
            __rafiki_forward_running "$state_dir" "$target" "$port"; or break
            sleep 0.05
        end
        if __rafiki_forward_running "$state_dir" "$target" "$port"
            echo "A sessão da porta $port ainda está ativa." >&2
            return 1
        end
        echo "Parada: porta $port."
        return 0
    end

    if test "$action" = stop
        if test -S "$socket"; and not test -L "$socket"
            command rm -f -- "$socket"; or return 1
        end
        echo "Já estava inativa: porta $port; nenhum outro processo foi alterado."
        return 0
    end
    if __rafiki_forward_occupied "$port"
        echo "Porta $port ocupada por outro processo; não foi alterada." >&2
        return 1
    end
    if test -S "$socket"; and not test -L "$socket"
        # A dead master can leave a socket behind after an abrupt shutdown.
        command rm -f -- "$socket"; or return 1
    else if test -e "$socket"; or test -L "$socket"
        echo "Caminho de controle inesperado para a porta $port; preservado." >&2
        return 1
    end

    command ssh -M -S "$socket" -fnNT \
        -o ControlMaster=yes -o ControlPersist=no \
        -o ExitOnForwardFailure=yes -o GatewayPorts=no \
        -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
        -o ConnectTimeout=10 -o ConnectionAttempts=1 -o BatchMode=yes \
        -L "127.0.0.1:$port:127.0.0.1:$port" "$target" >/dev/null 2>"$state_dir/p$port.log"
    set -l result $status
    if test "$result" -ne 0
        command cat -- "$state_dir/p$port.log" >&2
        echo "Falha ao abrir a porta $port (SSH: $result)." >&2
        return 1
    end
    if not __rafiki_forward_running "$state_dir" "$target" "$port"
        echo "SSH não confirmou a sessão de controle da porta $port." >&2
        return 1
    end
    echo "Aberta: 127.0.0.1:$port → $target/127.0.0.1:$port."
end

function rafiki-forward --description 'Abre, consulta e encerra portas SSH do rafiki'
    set -l target core@rafiki
    set -l state_root "$HOME/.local/state"
    if set -q XDG_STATE_HOME; and test -n "$XDG_STATE_HOME"
        set state_root "$XDG_STATE_HOME"
    end
    set -l state_dir "$state_root/rafiki-forward"
    set -l function_file (status filename)
    set -l action status
    set -l ports
    set -l result 0
    set -l all 0
    set -l args $argv

    if test -e "$state_dir"; or test -L "$state_dir"
        if test -L "$state_dir"; or not test -d "$state_dir"; or not test -O "$state_dir"
            echo "Diretório de controle inseguro: $state_dir" >&2
            echo 'Status atual indisponível: diretório de controle não utilizado.'
            return 1
        end
    end

    if test (count $args) -gt 0
        switch "$args[1]"
            case stop
                set action stop
                set args $args[2..]
                if test (count $args) -eq 1; and test "$args[1]" = all
                    set all 1
                    set args
                else if test (count $args) -eq 0
                    echo 'Informe as portas ou use: rafiki-forward stop all' >&2
                    set result 2
                end
            case status
                set args $args[2..]
                if test (count $args) -gt 0
                    echo 'Uso: rafiki-forward status' >&2
                    set result 2
                    set args
                end
            case -h --help help
                printf 'Uso:\n  rafiki-forward                  Mostrar status\n'
                printf '  rafiki-forward 8080 8000        Abrir somente as portas que faltam\n'
                printf '  rafiki-forward stop 8080 8001   Parar portas específicas\n'
                printf '  rafiki-forward stop all         Parar todos os túneis gerenciados\n'
                if test (count $args) -gt 1
                    set result 2
                end
                set args
            case '*'
                set action start
        end
    end

    for arg in $args
        set -l port (__rafiki_forward_port "$arg")
        if test $status -ne 0
            echo "Porta inválida: '$arg'. Use números de 1 a 65535." >&2
            set result 2
        else if not contains -- "$port" $ports
            set -a ports "$port"
        end
    end
    if test "$all" -eq 1
        set ports (__rafiki_forward_tracked "$state_dir")
        if test (count $ports) -eq 0
            echo 'Nenhum túnel gerenciado para parar.'
        end
    end

    if test "$result" -eq 0; and test "$action" != status; and test (count $ports) -gt 0
        # OpenSSH appends a temporary suffix while creating its Unix socket.
        set -l socket_bytes (printf '%s' "$state_dir/p65535.sock" | command wc -c | string trim)
        if test "$socket_bytes" -gt 85
            echo 'Caminho de controle longo demais; use um XDG_STATE_HOME mais curto.' >&2
            set result 1
        else if not command mkdir -p -m 700 -- "$state_dir"; or not command chmod 700 "$state_dir"
            echo 'Não foi possível preparar o diretório privado de controle.' >&2
            set result 1
        else
            for port in $ports
                # Keep the lock file to avoid unlink/recreate races between shells.
                command lockf -k -t 12 "$state_dir/p$port.lock" \
                    (status fish-path) --no-config -c \
                    'source "$argv[1]"; __rafiki_forward_change $argv[2..]' \
                    "$function_file" "$state_dir" "$target" "$action" "$port"
                if test $status -ne 0
                    echo "Não foi possível concluir a operação na porta $port." >&2
                    set result 1
                end
            end
        end
    end
    __rafiki_forward_status "$state_dir" "$target" $ports
    return "$result"
end
