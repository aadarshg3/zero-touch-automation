
intf = "g0/1"

sw_config_data = {
    "intf": intf,
    "desc": "connected to user port",
    "speed": 1000,
    "duplex": "full"
}

sw_config_syntax = {
    "intf": "interface {}",
    "desc": "description {}",
    "speed": "speed {}",
    "duplex": "duplex {}"
}

for k, v in sw_config_data.items():
   print(sw_config_syntax[k].format(v))