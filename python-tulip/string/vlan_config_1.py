

# for item in range(2,11):
#     print("vlan " + str(item))
#     # print(" name" + " " + "name_" + str(item))
#     print(" name", "name_" + str(item))
    

# for vlan in range(1,30):
#     print("vlan", str(vlan) + str(0))
    
# for item in range(1,11):
#     item =item*10
#     print("vlan " + str(item))
#     print("name " + "name_" + str(item))
    
# for item in range(1,11):
    
#     print("vlan " + str(item*10))
#     print("name " + "name_" + str(item*10))


# for item in range (2,11):
#     if item != 3 and item != 7 : 
#         print("vlan" + str(item*10))
#         print("name" ,"name_" +str(item*10))
        
# for item in range(1,11):
#     if (item != 3) and (item != 7):
#         print("vlan " + str(item) + str(0))

# for item in range(1,11):
#     if (item == 3) or (item == 7):
#         continue
#     else:
#         print("vlan " + str(item) + str(0))

for item in range(1,11):
    if item not in [3,7]:
        print("vlan " + str(item) + str(0))
