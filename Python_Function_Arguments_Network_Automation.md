# 🧠 Python Function Arguments – Network Automation Context

This document explains the **four major types of function arguments** in Python — with practical **network automation examples** inspired by Python scripts used in tools like NAPALM, Netmiko, and REST API integrations.

---

## ⚙️ 1. Positional Arguments

**Definition:**  
Arguments that are **passed in order** and must **match the function parameters exactly**.

### 🧩 Example
```python
def connect_device(vendor, ip):
    print(f"Connecting to {vendor} device at {ip}")
    return f"Connected to {vendor} - {ip}"

result = connect_device("Cisco", "192.168.1.10")
print(result)
print(type(result))
```

### ✅ Output
```
Connecting to Cisco device at 192.168.1.10
Connected to Cisco - 192.168.1.10
<class 'str'>
```

### ⚠️ Common Error
If one positional argument is missing:
```python
connect_device("Cisco")
```
**Error:**
```
TypeError: connect_device() missing 1 required positional argument: 'ip'
```

---

## 🧮 2. Variable Positional Arguments (`*args`)

**Definition:**  
Allows **multiple positional values** to be passed into a function as a **tuple**.

### 🧩 Example
```python
def add_vlan_ids(*vlans):
    print("Received VLAN IDs:", vlans)
    return sum(vlans)

total_vlans = add_vlan_ids(10, 20, 30)
print(total_vlans)
print(type(total_vlans))
```

### ✅ Output
```
Received VLAN IDs: (10, 20, 30)
60
<class 'int'>
```

### 🧠 Explanation
- All values go into a **tuple** (`(10, 20, 30)`).
- Useful when VLAN list length is dynamic.

### ⚠️ Common Error
If specific positional args expected **before `*args`** are missing:
```python
def device_info(vendor, *details):
    print(vendor, details)

device_info()
```
**Error:**
```
TypeError: device_info() missing 1 required positional argument: 'vendor'
```

---

## 🔑 3. Keyword Arguments

**Definition:**  
Arguments that are **passed using key=value** pairs.  
Order doesn’t matter.

### 🧩 Example
```python
def configure_interface(interface, ip, mask):
    print(f"Interface: {interface}, IP: {ip}/{mask}")

configure_interface(interface="Gig0/1", mask="24", ip="10.10.10.1")
```

### ✅ Output
```
Interface: Gig0/1, IP: 10.10.10.1/24
```

### ⚠️ Common Error
If a keyword is misspelled:
```python
configure_interface(intface="Gig0/1", ip="10.10.10.1", mask="24")
```
**Error:**
```
TypeError: configure_interface() got an unexpected keyword argument 'intface'
```

---

## 🧰 4. Keyword Variable Arguments (`**kwargs`)

**Definition:**  
Collects multiple **key=value pairs** into a **dictionary**.  
Perfect for dynamic configurations (like JSON payloads).

### 🧩 Example
```python
def build_payload(**device_info):
    print(device_info)
    return device_info

payload = build_payload(hostname="router1", ip="192.168.1.1", vendor="Juniper")
print(type(payload))
```

### ✅ Output
```
{'hostname': 'router1', 'ip': '192.168.1.1', 'vendor': 'Juniper'}
<class 'dict'>
```

### 🧠 Explanation
- Converts input to a dictionary.
- Ideal for REST API body creation:
  ```python
  {"hostname": "router1", "ip": "192.168.1.1", "vendor": "Juniper"}
  ```

---

## 🧩 Combined Example – All Argument Types Together

### 💻 Example
```python
def device_summary(vendor, ip, *features, **credentials):
    print("Vendor:", vendor)
    print("IP Address:", ip)
    print("Features:", features)
    print("Credentials:", credentials)

device_summary(
    "Cisco",
    "10.10.10.10",
    "SSH", "NETCONF",
    username="admin",
    password="cisco123"
)
```

### ✅ Output
```
Vendor: Cisco
IP Address: 10.10.10.10
Features: ('SSH', 'NETCONF')
Credentials: {'username': 'admin', 'password': 'cisco123'}
```

### 🧠 Type Summary
| Argument Type | Data Type | Example Input | Example Value |
|----------------|------------|----------------|----------------|
| Positional | as-is | "Cisco" | string |
| Variable Positional (`*args`) | tuple | "SSH", "NETCONF" | ('SSH', 'NETCONF') |
| Keyword | named | username="admin" | string |
| Keyword Variable (`**kwargs`) | dict | { "username": "admin", "password": "cisco123" } | dict |

---

## 🧩 Common Errors Reference

| Type | Mistake | Example | Error |
|------|----------|----------|--------|
| Missing positional | Missing an arg | connect_device("Cisco") | TypeError: missing 1 required positional argument |
| Extra positional | Too many args | add_vlan_ids(10, 20, 30, 40, 50, "test") | TypeError |
| Wrong keyword | Typo in name | configure_interface(intface="Gi0/1") | TypeError: unexpected keyword |
| Order error | Keyword before positional | add_vlan_ids(vlan=10, 20) | SyntaxError: positional argument follows keyword argument |

---

## 🧭 Order of Arguments in Python

When defining a function, the correct order is:

```
def func(positional, *args, keyword, **kwargs):
```

✅ **Order must always be:**
1. Positional arguments  
2. `*args`  
3. Keyword arguments  
4. `**kwargs`

### Example:
```python
def network_func(host, *args, timeout=10, **kwargs):
    pass
```

---

## 🏁 Summary

| Argument Type | Syntax | Data Type | Example |
|----------------|---------|-------------|----------|
| Positional | def f(a, b) | Any | f(10, 20) |
| Variable Positional | def f(*args) | tuple | f(10, 20, 30) |
| Keyword | def f(x=10) | Any | f(x=20) |
| Variable Keyword | def f(**kwargs) | dict | f(a=10, b=20) |

---

### 💡 Pro Tip (Network Engineers)
When building network automation functions:
- Use `*args` for flexible lists (e.g., VLAN IDs, IPs).
- Use `**kwargs` for API payloads or CLI options.
- Always validate argument count to avoid TypeError.

---

**Author:** _Aadarsh Kumar Gupta_  
**Context:** Network Automation Study Notes (Python Fundamentals)  
**Date:** November 2025
