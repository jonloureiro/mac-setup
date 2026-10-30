# Everforest for Slack

[everforest.txt](everforest.txt) contains only the theme string to paste into
Slack's **Import theme** dialog. Slack imports pasted text, not a file upload.

This is an adaptation of the dark Everforest appearance shown in the Codex
reference screenshot, using the official Everforest dark, medium palette.
The cream selection echoes the screenshot's warm foreground; green and coral
provide presence and notification accents.

| Position | Slack field | Everforest color | Hex |
| --- | --- | --- | --- |
| 1 | System navigation | `bg0` | `#2D353B` |
| 2 | Selected items | `fg` | `#D3C6AA` |
| 3 | Presence indication | `green` | `#A7C080` |
| 4 | Notifications | `red` | `#E67E80` |

## Import

1. Open `everforest.txt` and copy its entire line.
2. In Slack, open **Preferences → Appearance**, choose **Dark**, and open
   **Custom theme → Import**.
3. Paste the line into **Paste in a theme string**, then click **Apply**.
4. Leave **Window gradient** off for solid colors. Save changes if prompted.

The string covers Slack's four custom theme fields. It does not control every
surface or text color, so Slack will not reproduce the entire Codex interface.
The file's syntax was checked locally; applying it in Slack remains a manual step.

## Sources

- [Everforest palette](https://github.com/sainnhe/everforest/blob/master/palette.md)
  for the original color values.
- [Slack theme documentation](https://slack.com/help/articles/205166337-Change-your-Slack-theme)
  for the import workflow.
- [Codigrate Slack themes](https://github.com/codigrate/slack-themes#theme-format)
  for the four-color string order, matching the supplied Slack preferences screenshot.

Sources checked on 2026-10-30.
