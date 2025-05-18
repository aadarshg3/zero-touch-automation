
dict_data = {
    "data1": "This is the second class for dictionary",
    "data2": ["Ravi", "Prince", 10, [ {"a": "a1"}, {"b": "b22"}, {"c": "c1"}], 200, 20.3],
    "data3": {"key1": "Hello world 1",
              "key2": ["Ravi", "Prince", 10, [ {"a": "a1"}, [{"b": "b22"}, {"c": [1,2,3,4]}]], 200, 20.3],
              "key3": "Hello world 3",
              },
    "data4": [ {"a": "a1"}, {"b": {"key1": "Hello world 1",
              "key2": ["Ravi", "Prince", 10, [ {"a": "a1"}, [{"b": [ {"a": "a1"}, {"b": "b22"}, {"c": "c1"}]}, {"c": [1,2,3,4]}]], 2000, 20.3],
              "key3": "Hello world 3",
              }}, {"c": "c1"}],
}

print(int(dict_data['data4'][1]["b"]['key2'][-1]))
# print(dict_data.get("data2")[1])
# print(dict_data["data3"]["key2"])
# print(dict_data["data4"][1]["b"])
# print(dict_data["data3"]["key2"][3][1][1]["c"][2])



