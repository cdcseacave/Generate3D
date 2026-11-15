#!/bin/zsh
# Start a headless Blender that serves the Blender Lab MCP add-on bridge.
# Uses port 9877 so it never collides with a GUI Blender on the default 9876.
#
# The MCP add-on is currently only installed in the Blender 5.2 profile, so we
# point this instance at that extensions folder instead of touching the 5.3 one.
PORT="${BLENDER_MCP_PORT:-9877}"
export BLENDER_USER_EXTENSIONS="${BLENDER_USER_EXTENSIONS:-$HOME/Library/Application Support/Blender/5.2/extensions}"
exec /Applications/Blender.app/Contents/MacOS/Blender --background --online-mode \
  --addons bl_ext.user_default.mcp \
  --command blender_mcp --port "$PORT"
