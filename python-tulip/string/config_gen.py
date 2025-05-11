
dst_ip = input("Enter destination ip:")
src_ip = input("Enter source ip:")

# ping_command = "ping {} source {}"

# config = ping_command.format(dst_ip, src_ip)

config = f"ping {dst_ip} source {src_ip}"
print(config)

