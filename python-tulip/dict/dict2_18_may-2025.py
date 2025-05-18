dict_data = {
    "data1": "This is the second class for dictionary",
    "data2": ["k", "v", 10, [ {"a": "a1"}, {"b": "b22"}, {"c": "c1"}], 200, 20.3],
    "data3": {"key1": "Hello world 1",
              "key2": ["Ravi", "Prince", 10, [ {"a": "a1"}, [{"b": "b22"}, {"c": [1,2,3,4]}]], 200, 20.3],
              "key3": "Hello world 3",
              },
    "data4": [ {"a": "a1"}, {"b": {"key1": "Hello world 1",
              "key2": ["Ravi", "Prince", 10, [ {"a": "a1"}, [{"b": [ {"a": "a111"}, {"b": "b22"}, {"c": "c1"}]}, {"c": [1,2,3,4]}]], 2000, 20.3],
              "key3": "Hello world 4",
              }}, {"c": "c1"}],
}


# print(dict_data["data4"][1]["b"]["key2"][3][1][0]["b"][0]["a"])
print(dict_data["data4"][1]["b"]["key2"][3][1][1]["c"][1])




# print(dict_data["data4"][1]["b"]["key2"][3][1][0])


# Que1) print full from given data

# data = {"devices": [('intf', 'Gig0/1'), ('bandwidth', 1000), ('speed', 1000), ('duplex', 'full')]}
# print(data["devices"][3][1])


# Que2) print full from given data
# data = {"devices": {'intf': 'Gig0/1', 'bandwidth': 1000, 'speed': 1000, 'duplex': 'full'}}
# print((data)["devices"]["duplex"])

# Que:3) Print 500 from bandwidth

# data = {"devices": { "intf": "Gig0/1", "bandwidth": [('intf', 'Gig0/1'), ('bandwidth', 500), ('speed', 1000), ('duplex', 'full')], "speed": 1000, "duplex": "full"}}
# print(data["devices"]["bandwidth"][1][1])

# Que:4) "Print Hello world 3" from below given data: ==> # print(dict_data["data3"]["key3"])
# Que:5) "Print a111" from below given data: ==> # print(dict_data["data4"][1]["b"]["key2"][3][1][0]["b"][0]["a"])
# Que:6) "Print 2 of key c" from below given data:===> print(dict_data["data4"][1]["b"]["key2"][3][1][1]["c"][1])


# dict_data = {
#     "data1": "This is the second class for dictionary",
#     "data2": ["k", "v", 10, [ {"a": "a1"}, {"b": "b22"}, {"c": "c1"}], 200, 20.3],
#     "data3": {"key1": "Hello world 1",
#               "key2": ["Ravi", "Prince", 10, [ {"a": "a1"}, [{"b": "b22"}, {"c": [1,2,3,4]}]], 200, 20.3],
#               "key3": "Hello world 3",
#               },
#     "data4": [ {"a": "a1"}, {"b": {"key1": "Hello world 1",
#               "key2": ["Ravi", "Prince", 10, [ {"a": "a1"}, [{"b": [ {"a": "a111"}, {"b": "b22"}, {"c": "c1"}]}, {"c": [1,2,3,4]}]], 2000, 20.3],
#               "key3": "Hello world 4",
#               }}, {"c": "c1"}],
# }








# data = {"devices": ["R1", "R2", "R3"]}

# print(data["devices"])
# print(type(data)) # dict
# print(data["devices"])
# print(type(data["devices"])) # list
# print(data["devices"][1])
# print(data["devices"][1][0])
