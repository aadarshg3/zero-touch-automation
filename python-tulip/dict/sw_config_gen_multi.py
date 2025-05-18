
sw_config_data = [
    {
    "intf": "ge0/1",
    "desc": "connected to user port",
    "speed": 1000,
    "duplex": "full"
    },
    {
    "intf": "ge0/2",
    "desc": "connected to server",
    "speed": "auto",
    "duplex": "half"
    },
    {
    "intf": "ge0/3",
    "desc": "connected to user port",
    "speed": 1000,
    "duplex": "full"
    }   
]

sw_config_syntax = {
    "intf": "interface {}",
    "desc": "description {}",
    "speed": "speed {}",
    "duplex": "duplex {}"
}

for conf in sw_config_data:
    print("!")
    print(conf)
    for k, v in conf.items():
        print(sw_config_syntax[k])