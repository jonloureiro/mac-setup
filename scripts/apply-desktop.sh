#!/usr/bin/env sh
set -eu

# Dark icons + folder tint from RGB. Wallpaper from wallpapers/, or solid RGB if empty.
RGB="${1:-247 201 160}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
REPO_WALLPAPER_DIR="$(cd "$SCRIPT_DIR/.." && pwd -P)/wallpapers"
FALLBACK_DIR="$HOME/.local/share/wallpapers"
SOLID_WALLPAPER="$FALLBACK_DIR/solid.png"

mkdir -p "$FALLBACK_DIR"

python3 - "$RGB" "$SOLID_WALLPAPER" <<'PY'
import ctypes, struct, subprocess, sys, zlib

r, g, b = [int(x) for x in sys.argv[1].replace(",", " ").split()[:3]]
raw = (b"\x00" + bytes([r, g, b, 255]) * 128) * 128
png = (
    b"\x89PNG\r\n\x1a\n"
    + struct.pack(">I4sIIBBBBB", 13, b"IHDR", 128, 128, 8, 6, 0, 0, 0)
    + struct.pack(">I", zlib.crc32(b"IHDR" + struct.pack(">IIBBBBB", 128, 128, 8, 6, 0, 0, 0)) & 0xFFFFFFFF)
    + struct.pack(">I4sB", 1, b"sRGB", 0)
    + struct.pack(">I", zlib.crc32(b"sRGB\x00") & 0xFFFFFFFF)
    + struct.pack(">I4s", len(zlib.compress(raw)), b"IDAT")
    + zlib.compress(raw)
    + struct.pack(">I", zlib.crc32(b"IDAT" + zlib.compress(raw)) & 0xFFFFFFFF)
    + struct.pack(">I4sI", 0, b"IEND", zlib.crc32(b"IEND") & 0xFFFFFFFF)
)
with open(sys.argv[2], "wb") as f:
    f.write(png)

rf, gf, bf = r / 255.0, g / 255.0, b / 255.0

# Apply dark icon style (2 = RegularDark) and folder tint color matching RGB
try:
    objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
    ctypes.cdll.LoadLibrary("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight")
    appkit = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")
    cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")

    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]

    msg_id = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(("objc_msgSend", objc))
    msg_void = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)(("objc_msgSend", objc))
    msg_void_uint = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint)(("objc_msgSend", objc))
    msg_void_ptr = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(("objc_msgSend", objc))

    cg.CGColorCreateSRGB.restype = ctypes.c_void_p
    cg.CGColorCreateSRGB.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_double]
    cg_color = cg.CGColorCreateSRGB(rf, gf, bf, 1.0)

    cls = objc.objc_getClass(b"SLSIconAppearanceConfiguration")
    cfg = msg_id(cls, objc.sel_registerName(b"fetchCurrentIconAppearanceConfiguration"))
    msg_void_uint(cfg, objc.sel_registerName(b"setIconAppearanceTheme:"), 2)
    msg_void_uint(cfg, objc.sel_registerName(b"setIconTintColorName:"), 10)
    msg_void_ptr(cfg, objc.sel_registerName(b"setOtherIconTintColor:"), cg_color)
    msg_void(cfg, objc.sel_registerName(b"save"))

    appkit.NSColorSetUserAccentColor.argtypes = [ctypes.c_long, ctypes.c_bool]
    appkit.NSColorSetUserAccentColor(-2, True)
    subprocess.run(["defaults", "delete", "-g", "AppleHighlightColor"], stderr=subprocess.DEVNULL)
except Exception:
    pass
PY

sips --matchTo "/System/Library/ColorSync/Profiles/sRGB Profile.icc" "$SOLID_WALLPAPER" >/dev/null 2>&1 || true

SELECTED_IMAGE=""
if [ -d "$REPO_WALLPAPER_DIR" ]; then
  CURRENT_PIC="$(osascript -e 'tell application "System Events" to get picture of desktop 1' 2>/dev/null || true)"
  case "$CURRENT_PIC" in
    "$REPO_WALLPAPER_DIR"/*)
      [ -f "$CURRENT_PIC" ] && SELECTED_IMAGE="$CURRENT_PIC"
      ;;
  esac
  if [ -z "$SELECTED_IMAGE" ]; then
    for img in "$REPO_WALLPAPER_DIR"/*; do
      case "$img" in
        *.jpg|*.JPG|*.jpeg|*.JPEG|*.png|*.PNG|*.heic|*.HEIC|*.webp|*.WEBP)
          SELECTED_IMAGE="$img"
          break
          ;;
      esac
    done
  fi
fi

if [ -n "$SELECTED_IMAGE" ]; then
  osascript \
    -e "tell application \"System Events\" to tell every desktop to set pictures folder to \"$REPO_WALLPAPER_DIR\"" \
    -e "tell application \"System Events\" to tell every desktop to set picture to \"$SELECTED_IMAGE\""
else
  osascript -e "tell application \"System Events\" to tell every desktop to set picture to \"$SOLID_WALLPAPER\""
fi

killall Dock Finder || true
