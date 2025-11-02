# 🧠 Python Function Arguments (func2_arguments)

This documentation explains the use of **positional**, **variable positional**, **keyword**, and **keyword variable** arguments in Python using practical `add()` function examples — following Python best practices for clean network automation scripts.

> 📘 Note: Print statements are intentionally kept outside the functions, as functions should focus on returning data rather than printing it.

---

## ⚙️ 1. Positional Arguments

**Definition:**  
Positional arguments must be passed **in correct order** and **match exactly** the parameters defined.

### 🧩 Example
```python
def add(x, y):
    s = x + y
    return s

temp_var = add(20, 30)
print(temp_var)
print(type(temp_var))
```

### ✅ Output
```
50
<class 'int'>
```

### ⚙️ Common Error (Missing Argument)
```python
temp_var = add(20)
```
**Error:**
```
TypeError: add() missing 1 required positional argument: 'y'
```

### ⚙️ Common Error (Extra Argument)
```python
temp_var = add(20, 30, 50)
```
**Error:**
```
TypeError: add() takes 2 positional arguments but 3 were given
```

### 🌐 Network Example
When calculating total active network connections:
```python
def total_connections(active, standby):
    return active + standby

print(total_connections(50, 10))   # Output: 60
```

---

## 🧮 2. Variable Positional Arguments (`*args`)

**Definition:**  
Allows passing a **variable number of arguments**. All arguments are collected into a **tuple**.

### 🧩 Example
```python
def add(*vars):
    return vars

temp_var = add(20, 30, 400)
print(temp_var)
print(type(temp_var))
```

### ✅ Output
```
(20, 30, 400)
<class 'tuple'>
```

### 🌐 Network Example
Storing multiple VLAN IDs dynamically:
```python
def vlan_list(*vlans):
    return vlans

print(vlan_list(10, 20, 30))
```
**Output:**
```
(10, 20, 30)
```

### ⚙️ Common Error (No Arguments)
```python
temp_var = add()
print(temp_var)
```
**Output:**
```
()
<class 'tuple'>
```

---

## 🔑 3. Keyword Arguments

**Definition:**  
Keyword arguments are passed as **key=value** pairs. They improve readability and remove the need to remember argument order.

### 🧩 Example
```python
def add(x, y, z, *vars):
    s = 0
    for item in vars:
        s = s + item
    return s

sum_val = add(20, 30, 400, 11, 22, 5)
print(sum_val)
print(type(sum_val))
```

### ✅ Output
```
38
<class 'int'>
```

### 🌐 Network Example
Summing interface traffic counters dynamically:
```python
def total_traffic(interface, *traffic_values):
    return sum(traffic_values)

print(total_traffic("Gig0/1", 100, 200, 300))
```
**Output:**
```
600
```

### ⚙️ Common Error
When required positional arguments are not provided:
```python
add(20)
```
**Error:**
```
TypeError: add() missing 2 required positional arguments: 'y' and 'z'
```

---

## 🧰 4. Keyword Variable Arguments (`**kwargs`)

**Definition:**  
Used when argument names are unknown in advance. All are stored as a **dictionary**.

### 🧩 Example
```python
def add(**kvars):   
    return kvars

sum_val = add(a="ip1", b="ip2", c="ip3") 
print(sum_val)
print(type(sum_val))
```

### ✅ Output
```
{'a': 'ip1', 'b': 'ip2', 'c': 'ip3'}
<class 'dict'>
```

### 🌐 Network Example
Building device configuration payload dynamically:
```python
def device_config(**params):
    return params

print(device_config(hostname="router1", ip="192.168.1.1", os="ios"))
```
**Output:**
```
{'hostname': 'router1', 'ip': '192.168.1.1', 'os': 'ios'}
```

---

## 🧭 Argument Order in Python

When defining a function, the argument order **must always be**:

```
def func(positional, *args, keyword_defaults=None, **kwargs):
```

✅ **Execution Order:**
1. Positional arguments  
2. `*args` (variable positional)  
3. Keyword arguments (with defaults)  
4. `**kwargs` (variable keyword)

### Example:
```python
def network_add(x, *args, hostname=None, **kwargs):
    return x, args, hostname, kwargs

print(network_add(10, 20, 30, hostname="R1", location="DataCenter1"))
```
**Output:**
```
(10, (20, 30), 'R1', {'location': 'DataCenter1'})
```

---

## 🧩 Common Errors Summary

| Type | Mistake | Example | Error |
|------|----------|----------|--------|
| Missing positional | Missing an argument | `add(20)` | `TypeError: missing 1 required positional argument` |
| Extra positional | Too many arguments | `add(20, 30, 50)` | `TypeError: takes 2 positional arguments but 3 were given` |
| Wrong keyword | Invalid name | `add(x1=20, y=30)` | `TypeError: got an unexpected keyword argument 'x1'` |
| Keyword before positional | Wrong order | `add(x=20, 30)` | `SyntaxError: positional argument follows keyword argument` |

---

## 🧠 Summary Table

| Argument Type | Syntax | Data Type | Example | Output |
|----------------|--------|------------|----------|----------|
| Positional | `def add(x, y)` | Any | `add(20, 30)` | 50 |
| Variable Positional | `def add(*vars)` | tuple | `add(20, 30, 400)` | (20, 30, 400) |
| Keyword | `def add(x, y, z, *vars)` | int | `add(20, 30, 400, 11, 22, 5)` | 38 |
| Keyword Variable | `def add(**kvars)` | dict | `add(a="ip1", b="ip2", c="ip3")` | {'a': 'ip1', 'b': 'ip2', 'c': 'ip3'} |

---

**Author:** _Aadarsh Kumar Gupta_  
**Context:** Python Function Arguments – Based on Real Network Automation Use Cases  
**File Name:** func2_arguments.md  
**Date:** November 2025
