from helper import *
from com.dtmilano.android.viewclient import ViewClient
from local_pkg.client import LocalDeepClient
from requests import Session


device, serial = ViewClient.connectToDeviceOrExit()
client = ViewClient(device, serial)
client.dump()

local_client = LocalClient()
local_client.run()

local_deep_client = LocalDeepClient()
local_deep_client.run()

session = Session()
session.get("https://example.com")
