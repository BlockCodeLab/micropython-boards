include("$(PORT_DIR)/boards/manifest.py")

freeze("modules")

require("threading")
require("aiohttp")
require("aioble")
