dict_data = {
    "data1": "This is second class for dictionary",
    "data2": ["Ravi", "Prince", 10, [ {"a": "a1"}, {"b": "b22"}, {"c": "c1"}], 200, 20.3],
    "data3": {"key1": "Hello World 1",
              "key2": ["Ravi", "Prince", 10, [ {"a": "a1"}, [ {"b": "b22"}, {"c": [1,2,3,4]}]], 200, 20.312],
              },
    "data4": [{"a": "a1"}, {"b": {"key1": "Hello World 1",
              "key2": ["Ravi", "Princess", 10, [ {"a": "a1"}, [ {"b": "b22"}, {"c": [1,2,3,4]}]], 2000, 20.3],
              "key3": "Hello World 3",
              }}, {"c": "c1"}],
    
}


# print(dict_data["data3"]["key2"][3][1][1]["c"][2])
# print(dict_data["data4"][1]["b"]["key2"][4])
# print(dict_data["data4"][1]["b"]["key2"][-2])

#printing value a1 from data4 key:
print(dict_data["data4"][1]["b"]["key2"][3][0]["a"])

#printing value 4 under data4 key:
print(dict_data["data4"][1]["b"]["key2"][3][1][1]["c"][-1])

#printing value c1 under data4 key:
print(dict_data["data4"][-1]["c"])
# or
print(dict_data["data4"][2]["c"])

#printing value 10 from data3 key:
print(dict_data["data3"]["key2"][2])

#printing value 3 from data3 key:
print(dict_data["data3"]["key2"][3][1][1]["c"][2])


