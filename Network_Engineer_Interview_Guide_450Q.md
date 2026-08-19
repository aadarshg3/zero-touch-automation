---
title: "Network Engineer — Complete Technical Interview Guide"
subtitle: "450 Questions · 9 Domains · Senior/Principal Level (8+ Years)"
author: "Prepared for Aadarsh Gupta"
date: "August 2026"
geometry: "margin=2cm"
fontsize: 11pt
toc: true
toc-depth: 2
header-includes:
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{\small Network Engineer Interview Guide}
  - \fancyhead[R]{\small \thepage}
  - \fancyfoot[C]{}
  - \usepackage{enumitem}
  - \setlist{nosep}
---

\newpage

# SECTION 1: KUBERNETES NETWORKING (50 Questions)

## Q1. Explain the Kubernetes networking model and its three fundamental rules.

**Answer:** Kubernetes mandates three rules: (1) Every Pod gets a unique, cluster-wide routable IP address without manual allocation. (2) All Pods can communicate with all other Pods across nodes without NAT. (3) Nodes can reach Pods and vice versa without NAT. The CNI plugin implements these rules by creating veth pairs, assigning IPs from the node's pod CIDR, and programming routes or overlay tunnels. This pushes network complexity out of the application layer.

```
kubectl get pods -o wide   # Shows Pod IPs and node placement
```

## Q2. What is a CNI plugin and how does Kubelet interact with it?

**Answer:** CNI (Container Network Interface) is a specification defining ADD, DEL, CHECK operations. When Kubelet creates a Pod, it creates the pause container (holding the network namespace), then calls the CNI binary (e.g., `/opt/cni/bin/calico`) with the namespace path via stdin JSON. The CNI binary creates a veth pair, assigns an IP from IPAM, sets default routes inside the namespace, and returns the assigned IP. CNI config lives in `/etc/cni/net.d/`. Multiple plugins can be chained.

```
ls /etc/cni/net.d/            # CNI configuration files
ls /opt/cni/bin/               # CNI plugin binaries
```

## Q3. Explain the pause container and why it exists.

**Answer:** The pause container (registry.k8s.io/pause:3.9, ~700KB) holds the network namespace for the Pod. All other containers join this namespace via `--net=container:<pause-id>`, sharing the same IP, interfaces, and port space. If a user container crashes and restarts, the network namespace persists because the pause container is still running — the Pod's IP and network connections survive container restarts.

## Q4. How does a Pod get its IP address? Trace the full lifecycle.

**Answer:** (1) API server accepts Pod spec, scheduler assigns a node. (2) Kubelet receives the spec. (3) Kubelet calls CRI to create the sandbox (pause container) and new network namespace. (4) Kubelet invokes the CNI plugin with the namespace path. (5) CNI calls IPAM module — `host-local` allocates from the node's CIDR range. (6) CNI creates a veth pair: one end (eth0) in Pod namespace, other end (caliXXX/vethXXX) in host namespace. (7) CNI assigns IP to eth0, sets default route. (8) CNI returns IP to Kubelet. (9) Kubelet updates Pod status in the API server.

```
ip link show type veth                    # List veth interfaces on node
cat /var/lib/cni/networks/calico/         # IPAM allocations
```

## Q5. Compare Calico's BGP mode vs VXLAN mode.

**Answer:** **BGP mode:** Calico runs BIRD on each node. Nodes peer via BGP and exchange pod CIDR routes. Traffic is routed natively at L3 — no encapsulation overhead, no MTU penalty. Requires the physical network to route Pod CIDRs. Best for on-prem with BGP-capable ToR switches.

**VXLAN mode:** Pod traffic encapsulated in VXLAN (50-byte overhead). Underlying network only routes node IPs. Works everywhere (cloud, restricted networks). MTU reduced to 1450. Slight CPU overhead.

**Decision:** On-prem with controllable infrastructure → BGP. Cloud or restricted networks → VXLAN. Mixed → CrossSubnet option (BGP within same L2, VXLAN across L3).

```
calicoctl node status                     # BGP peering state
calicoctl get ippool -o yaml              # VXLAN vs BGP config
```

## Q6. How does Cilium replace kube-proxy? What is socket-level load balancing?

**Answer:** Cilium hooks an eBPF program into the `connect()` syscall. When Pod A calls `connect(ClusterIP:80)`, the eBPF program intercepts before any packet is built, resolves the ClusterIP to a backend Pod IP using an eBPF hash map (O(1) lookup), and rewrites the socket's destination. The kernel builds the packet with the backend IP as destination from the start. No DNAT, no conntrack entry, no reverse translation. This eliminates entire iptables chains. At 10,000+ Services, eBPF maintains constant performance while iptables degrades linearly.

```
cilium status                             # Health and kube-proxy replacement
cilium service list                       # All Services in eBPF map
cilium bpf lb list                        # Load balancer entries
```

## Q7. Explain Kubernetes Service types: ClusterIP, NodePort, LoadBalancer, ExternalName.

**Answer:** **ClusterIP:** Virtual IP from service CIDR. Internal-only. Exists only as iptables/IPVS rules — no interface holds this IP. **NodePort:** Extends ClusterIP. Opens port 30000-32767 on every node. External traffic → NodeIP:NodePort → DNAT to ClusterIP → DNAT to Pod. **LoadBalancer:** Extends NodePort. Cloud controller provisions external LB pointing at NodePorts. On bare metal: MetalLB. **ExternalName:** DNS CNAME only. No proxy, no ClusterIP. Aliases external services into cluster DNS.

```
kubectl get svc -o wide                   # All services with type
iptables-save | grep <ClusterIP>          # Trace DNAT rules
ipvsadm -Ln                              # IPVS virtual servers
```

## Q8. What is externalTrafficPolicy and how does it affect source IP?

**Answer:** **Cluster (default):** Any node handles traffic, even without local backend Pods. Extra hop + SNAT = source IP lost. Even distribution across nodes. **Local:** Only nodes with backend Pods accept traffic. No extra hop, source IP preserved. Uneven distribution. External LB must health-check NodePort per node.

**When to use Local:** Any time client source IP is needed — logging, geo-restriction, rate limiting, WAF. Common with Ingress Controllers.

## Q9. How does CoreDNS work in Kubernetes?

**Answer:** CoreDNS runs as a Deployment in kube-system (typically 2 replicas), exposed via ClusterIP Service (often 10.96.0.10). Every Pod's `/etc/resolv.conf` points to this IP. Corefile plugin chain: `kubernetes` plugin handles cluster-internal resolution, `forward` sends external queries upstream, `cache` caches responses.

Pod's resolv.conf contains search domains: `<ns>.svc.cluster.local svc.cluster.local cluster.local` with `ndots:5`.

```
kubectl -n kube-system get cm coredns -o yaml         # Configuration
kubectl exec -it <pod> -- nslookup kubernetes.default  # Test resolution
```

## Q10. Explain the ndots:5 problem and how to fix it.

**Answer:** Default ndots:5 means hostnames with fewer than 5 dots get search domain suffixes appended first. `api.example.com` (2 dots) triggers 4 wasted DNS queries before the real query. Fixes: (1) Trailing dot: `api.example.com.` bypasses search domains. (2) Reduce ndots in Pod spec dnsConfig: `ndots: "2"`. (3) Use `dnsPolicy: Default` for node's resolv.conf. (4) Deploy node-local-dns cache to reduce CoreDNS load.

## Q11. What is a Headless Service?

**Answer:** A Service with `clusterIP: None`. No VIP allocated. DNS returns individual Pod IPs (A records per Pod). Use cases: StatefulSets (each Pod gets stable DNS: `pod-0.svc.ns.svc.cluster.local`), gRPC client-side load balancing (gRPC needs all backend IPs), service discovery without proxy (Kafka brokers, Cassandra seeds).

## Q12. Explain EndpointSlices vs Endpoints.

**Answer:** Original Endpoints: single object with ALL Pod IPs for a Service. 5,000-Pod Service = one massive ~1.5MB object rewritten on every Pod change. EndpointSlices (GA since 1.21): chunks of ~100 endpoints. 5,000 Pods = ~50 slices. Pod change updates only its slice. Reduces API server load by orders of magnitude. Adds dual-stack support, topology hints, and per-endpoint conditions.

## Q13. What is kube-proxy and what modes does it support?

**Answer:** DaemonSet on every node. Watches Service/EndpointSlice changes, programs data plane. **iptables (default):** DNAT chains, O(n) rule traversal, slow at 5000+ Services. **IPVS:** Hash-based O(1) lookup, supports rr/lc/sh/wrr algorithms, scales to 10,000+ Services. **nftables:** Newer replacement for iptables with atomic updates. **none:** Disabled when Cilium replaces it.

```
kubectl -n kube-system get cm kube-proxy -o yaml | grep mode
iptables -t nat -L KUBE-SERVICES -n       # iptables mode
ipvsadm -Ln                                # IPVS mode
```

## Q14. Explain NetworkPolicy behavior.

**Answer:** Without NetworkPolicy: default-allow. When ANY NetworkPolicy selects a Pod via podSelector, that Pod shifts to default-deny for the specified direction (Ingress/Egress). Only explicitly allowed traffic passes. Policies are additive — no deny action in standard API. Requires a supporting CNI (Calico, Cilium, Antrea). Flannel does NOT enforce NetworkPolicy.

**Default deny all ingress:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes: [Ingress]
```

## Q15. Write a NetworkPolicy allowing DNS egress and specific Pod-to-Pod communication.

**Answer:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: backend-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      role: backend
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
      ports:
        - {protocol: TCP, port: 8080}
  egress:
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
    - to:
        - podSelector:
            matchLabels:
              role: database
      ports:
        - {protocol: TCP, port: 5432}
```

**Critical:** Forgetting DNS egress rule when specifying Egress policyType breaks all DNS resolution for selected Pods.

## Q16. How does Kubernetes Ingress work?

**Answer:** Ingress resource defines L7 routing rules (host/path-based) for HTTP/HTTPS. Requires an Ingress Controller (NGINX, Traefik, HAProxy) — a Pod running a reverse proxy that watches Ingress resources and dynamically configures routing. Controller exposed via Service (LoadBalancer/NodePort). Traffic flow: Client → LB → Ingress Controller Pod → reads rules → routes to backend Service → DNAT to Pod. TLS terminated at the controller using certs from Kubernetes Secrets.

## Q17. Explain Gateway API improvements over Ingress.

**Answer:** Gateway API separates concerns: **GatewayClass** (infra provider — like StorageClass), **Gateway** (cluster operator — listeners, ports, TLS), **HTTPRoute/TCPRoute/GRPCRoute** (developer — routing rules). Improvements: role-based separation, first-class TCP/UDP/gRPC support, native traffic splitting (canary), header modification without annotations, cross-namespace routing with permissions, portable across implementations.

## Q18. What is IPAM in Kubernetes? Compare host-local vs Calico IPAM.

**Answer:** **host-local:** Each node gets fixed CIDR (e.g., /24). Sequential allocation. Wastes IPs — 10 Pods on a /24 node wastes 244 IPs. **Calico IPAM:** Dynamic block allocation (/26 blocks, 64 IPs). Blocks assigned on demand. If freed, returned to pool. More efficient. Supports multiple IP pools for different workloads.

```
calicoctl ipam show --show-blocks         # Block allocation per node
```

## Q19. How does DNS work for StatefulSets?

**Answer:** StatefulSets require a Headless Service. Each Pod gets predictable DNS: `<pod-name>.<headless-svc>.<ns>.svc.cluster.local`. Pod `mysql-0` with service `mysql-svc` in namespace `db` → `mysql-0.mysql-svc.db.svc.cluster.local`. Stable across rescheduling — Pod IP changes but DNS name resolves to new IP. Enables database replication topologies where clients address specific replicas.

## Q20. Explain VXLAN in Kubernetes overlay networking.

**Answer:** VXLAN encapsulates L2 frames in UDP (port 4789) with 24-bit VNI. Pod A on Node 1 sends to Pod B on Node 2: the VXLAN interface on Node 1 wraps the original packet in UDP with outer headers src=Node1, dst=Node2. Node 2 decapsulates and delivers. Overhead: 50 bytes/packet. Effective MTU: 1450. Underlay only needs to route node IPs.

```
ip -d link show flannel.1       # VXLAN interface details
bridge fdb show dev flannel.1   # MAC-to-VTEP mapping
tcpdump -i eth0 port 4789       # Capture VXLAN traffic
```

## Q21. What is eBPF and why is it important for networking?

**Answer:** eBPF runs sandboxed programs in the Linux kernel without kernel modifications. Programs are JIT-compiled for near-native performance. Network hooks: XDP (before socket buffer — fastest, DDoS mitigation), tc (traffic control — Cilium policy enforcement), cgroup/connect4 (socket-level — Service load balancing), sockops (connection acceleration). Replaces iptables with O(1) hash-map lookups. Enables L7 policy in-kernel without sidecars.

## Q22. How does Hubble provide observability?

**Answer:** eBPF programs at tc hooks emit per-flow events into a ring buffer. Hubble reads and provides: identity-aware flow logs (Pod/namespace/labels, not just IPs), service dependency maps, L7 visibility (HTTP codes, paths, gRPC methods, DNS) without sidecars, NetworkPolicy verdict logging.

```
hubble observe --namespace production          # Namespace flows
hubble observe --verdict DROPPED               # Dropped traffic
hubble observe --protocol http                 # L7 HTTP flows
```

## Q23. Compare kube-proxy iptables vs IPVS mode.

**Answer:** **iptables:** Sequential chain traversal O(n). Random probability selection. Rule count = services × backends. Slow update at 5000+ services. **IPVS:** Hash-based O(1). Supports rr, lc, dh, sh, sed, nq. Handles 10,000+ services. Requires kernel modules (ip_vs, ip_vs_rr). Debug via `ipvsadm` instead of `iptables-save`.

## Q24. How does Pod-to-Service work with Cilium?

**Answer:** Pod calls `connect(ClusterIP:80)`. eBPF at cgroup/connect4 intercepts, looks up backend in eBPF lb4_services map, rewrites socket destination to PodIP:8080 using Maglev hashing. Kernel builds packet with PodIP as destination — no DNAT, no conntrack for translation. Return traffic translated back at socket level. Saves conntrack entries and packet processing vs iptables/IPVS.

## Q25. Kubernetes network troubleshooting methodology.

**Answer:** Layered: **L1 Pod-level:** `kubectl exec -- ip addr/route`, check veth pair on host. **L2 Node-level:** Same-node Pod-to-Pod works? Check CNI agent logs. **L3 Cross-node:** Check overlay (BGP peers via `calicoctl node status`, VXLAN interface up, UDP 4789 not blocked). **L4 Service-level:** ClusterIP reachable? Check kube-proxy rules, Endpoints populated. **L5 DNS:** `nslookup` from Pod. CoreDNS running? Service `kube-dns` has endpoints?

```
kubectl exec <pod> -- nslookup kubernetes.default
nsenter -t <pid> -n ip addr           # Enter Pod netns from host
conntrack -L -d <ClusterIP>           # Conntrack entries for Service
```

## Q26. What is a Service Mesh? Compare Istio and Linkerd.

**Answer:** Service Mesh adds L7 traffic management, mTLS, and observability via sidecar proxies. **Istio:** Control plane = istiod. Data plane = Envoy sidecars (~50-100MB RAM each). Full-featured: traffic splitting, circuit breaking, fault injection, mTLS, L7 metrics. **Linkerd:** linkerd2-proxy (Rust, ~10-20MB). Simpler: mTLS, retries, timeouts, metrics. Lower overhead. **Cilium Service Mesh:** eBPF-based, no sidecars — lowest overhead.

## Q27. How does mTLS work in a Service Mesh?

**Answer:** istiod acts as CA, issues X.509 certs to each sidecar using SPIFFE identity: `spiffe://cluster.local/ns/<ns>/sa/<sa>`. Pod A's Envoy initiates TLS to Pod B's Envoy. Both present and verify certs. Encrypted tunnel established. Traffic between sidecar and local app (localhost) is unencrypted but within same Pod namespace. Certs rotate automatically (24h default TTL) via SDS.

## Q28. What DaemonSets are used for networking components?

**Answer:** kube-proxy (iptables/IPVS rules per node), calico-node/cilium-agent (CNI config, policy enforcement, BGP daemon), node-local-dns (per-node DNS cache), MetalLB speaker (LB IP advertisement). Must tolerate control-plane taints if running on masters.

## Q29. Trace traffic from external client to a Pod behind an Ingress.

**Answer:** Client → DNS resolve → External LB → NodePort → kube-proxy DNAT to Ingress Controller Pod → TLS termination → Host/path matching → proxy to backend Service ClusterIP → DNAT to backend Pod. With externalTrafficPolicy: Local, LB sends directly to nodes running the controller, saving one hop.

## Q30. What is Topology Aware Routing?

**Answer:** Keeps Service traffic zone-local to reduce latency and cross-AZ costs. EndpointSlice controller adds topology hints. kube-proxy routes to same-zone backends preferentially. Enable via annotation `service.kubernetes.io/topology-mode: Auto`. Disables automatically when backend distribution is too skewed.

## Q31. How does MetalLB work for bare-metal LoadBalancer Services?

**Answer:** Two modes: **L2:** Speaker Pod on one node responds to ARP for Service external IP. All traffic to that node, then kube-proxy distributes. Single-node bottleneck. **BGP:** Each speaker peers with ToR switches, announces Service IP as /32. Network ECMP-distributes. True load balancing. Requires BGP-capable infrastructure.

## Q32. Explain dual-stack networking in Kubernetes.

**Answer:** Pods and Services get both IPv4 and IPv6 (GA since 1.23). Requirements: dual-stack node network, CNI support, cluster CIDR includes both families. Services can be SingleStack, PreferDualStack, or RequireDualStack. DNS returns both A and AAAA records.

## Q33. How do init containers relate to Pod networking?

**Answer:** Init containers share the Pod's network namespace. Networking use cases: Istio's istio-init runs iptables rules to redirect traffic through Envoy sidecar. Wait-for-dependency containers test connectivity before main app starts. Network configuration (loading eBPF programs).

## Q34. How does Calico enforce NetworkPolicy with iptables?

**Answer:** Felix translates NetworkPolicy to iptables filter rules. Per-interface chains on veth host-end (e.g., cali-tw-caliXXX). Default-drop if any policy selects the Pod, then explicit ALLOW rules. Uses ipsets for efficient matching — one rule per ipset vs one rule per IP.

```
iptables -L -n -v | grep cali         # Calico chains
ipset list                             # Pod IP groups
```

## Q35. What is CiliumNetworkPolicy vs standard NetworkPolicy?

**Answer:** Standard: L3/L4 only. CiliumNetworkPolicy adds: L7 rules (HTTP method/path, gRPC service, Kafka topic, DNS name), DNS-based egress (allow *.amazonaws.com with dynamic IP resolution), CIDR identity policies, node-level policies (CiliumClusterwideNetworkPolicy).

## Q36. Troubleshoot DNS resolution failures in a cluster.

**Answer:** (1) CoreDNS running? `kubectl -n kube-system get pods -l k8s-app=kube-dns`. (2) Service has endpoints? `kubectl -n kube-system get endpoints kube-dns`. (3) Test from Pod: `nslookup kubernetes.default`. (4) Check resolv.conf: nameserver matches kube-dns ClusterIP? (5) NetworkPolicy blocking UDP 53? (6) conntrack race condition? Deploy node-local-dns.

## Q37. CNM vs CNI.

**Answer:** CNM is Docker's native model (libnetwork). CNI is CNCF standard — simpler, runtime-agnostic, composable. Kubernetes chose CNI. All K8s networking plugins implement CNI. CNI won due to simpler interface and runtime independence.

## Q38. How does Ingress Controller handle TLS termination?

**Answer:** Ingress resource references a kubernetes.io/tls Secret with tls.crt and tls.key. Controller loads cert into its reverse proxy (nginx ssl_certificate). Client connects HTTPS, controller decrypts, proxies HTTP to backend. cert-manager automates provisioning from Let's Encrypt.

## Q39. Pod CIDR allocation to nodes.

**Answer:** Cluster Pod CIDR (e.g., 10.244.0.0/16) subdivided per node via `--node-cidr-mask-size` (default /24). Each Node object has `.spec.podCIDR`. 256 nodes × 254 Pods per node. Plan CIDRs to avoid overlap with node/service networks.

```
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.podCIDR}{"\n"}{end}'
```

## Q40. Zero-trust networking in Kubernetes.

**Answer:** (1) Default-deny NetworkPolicy everywhere. (2) mTLS via service mesh or Cilium mutual auth. (3) L7 authorization (Istio AuthorizationPolicy, CiliumNetworkPolicy). (4) Identity-based policies using ServiceAccounts. (5) Egress control with DNS-based policies. (6) Pod Security Standards preventing privilege escalation.

## Q41. NodePort vs HostPort.

**Answer:** NodePort: port on ALL nodes, kube-proxy manages, Service abstraction, 30000-32767. HostPort: port on the specific node running the Pod, no Service, scheduling constraint (two Pods can't share same hostPort on same node). HostPort rarely used in production.

## Q42. How does Kubernetes handle egress traffic?

**Answer:** Pod → veth → node routing table → SNAT (Pod source IP → node IP via MASQUERADE rule) → physical network → external destination. SNAT required because external routers don't know Pod CIDRs. Egress Gateway (Cilium/Istio) routes all egress through a dedicated node with known external IP for source IP consistency.

## Q43. Multi-cluster networking approaches.

**Answer:** Cilium ClusterMesh (eBPF-based, non-overlapping CIDRs required), Submariner (encrypted tunnels, supports overlapping CIDRs via Globalnet), Multi-Cluster Services API (KEP-1645, ServiceExport/ServiceImport), Istio multi-cluster (shared or replicated control planes).

## Q44. port vs targetPort vs nodePort.

**Answer:** port: Service ClusterIP listens on this (e.g., 80). targetPort: container's actual port (e.g., 8080). nodePort: external port on every node (e.g., 30080). Flow: External → NodeIP:30080 → ClusterIP:80 → PodIP:8080.

## Q45. Kubernetes network namespaces internals.

**Answer:** Each Pod gets its own Linux netns. Separate eth0, IP, routing table, iptables, socket space. Host sees all via `/proc/<pid>/ns/net`. Debugging: `nsenter -t $PID -n ip addr show`.

## Q46. SCTP support in Kubernetes.

**Answer:** Supported since v1.20 GA. Used in 5G/telecom (Diameter, S1AP, NGAP). Specify `protocol: SCTP` in Service/container ports. CNI must support it (Calico, Cilium do).

## Q47. Network Function Chaining in Kubernetes.

**Answer:** Approaches: Multus CNI (multiple interfaces per Pod), Cilium L7 with Envoy filters, Service Mesh filter chains, NSM (Network Service Mesh) for L2/L3 chaining.

## Q48. What is Multus CNI?

**Answer:** Meta-CNI that calls other CNI plugins to attach multiple network interfaces to a Pod. Default CNI provides eth0. Multus adds net1, net2, etc. Use cases: telecom NFV, SR-IOV, dedicated storage NICs. Configuration via NetworkAttachmentDefinition CRD.

## Q49. IPv6 networking in Kubernetes.

**Answer:** IPv6-only or dual-stack. No NAT needed (vast address space). Uses NDP instead of ARP. Calico and Cilium support IPv6. Most corporate networks lack IPv6 infrastructure — dual-stack provides migration path.

## Q50. Design a production K8s networking architecture.

**Answer:** CNI: Cilium (eBPF, kube-proxy replacement, L7 policy, Hubble). Pod CIDR: /16 cluster, /24 per node. Ingress: Gateway API + Envoy Gateway. NetworkPolicy: default-deny everywhere, CiliumNetworkPolicy for L7. Egress: Cilium egress gateway for predictable source IPs. Topology Aware Routing for zone-local traffic. NodeLocalDNS for per-node caching. Observability: Hubble + Prometheus + Grafana.


\newpage

# SECTION 2: BGP — BORDER GATEWAY PROTOCOL (50 Questions)

## Q1. What is BGP and why is it called a path vector protocol?

**Answer:** BGP is the only EGP in production use, exchanging reachability between Autonomous Systems. It's path vector because each route carries the full AS-PATH — the sequence of ASes traversed. This differs from distance-vector (only knows metric) and link-state (builds complete topology). AS-PATH serves dual purpose: loop prevention (drop routes containing own ASN) and path selection (shorter path preferred).

## Q2. Explain the BGP FSM states.

**Answer:** **Idle:** Not started. **Connect:** TCP SYN sent. **Active:** TCP attempts failing — NOT healthy despite the name. Common causes: peer unreachable, ACL blocking TCP 179, wrong peer IP. **OpenSent:** TCP up, OPEN message sent, waiting for peer's OPEN. **OpenConfirm:** OPEN exchanged, waiting for KEEPALIVE. **Established:** Fully operational, routes exchanged.

```
show bgp summary    # Neighbor states — should show Established with prefix count
```

## Q3. iBGP vs eBGP differences.

**Answer:** **eBGP:** Different ASes, TTL=1, next-hop changes, AS-PATH for loops, AD=20. **iBGP:** Same AS, TTL=255, next-hop preserved (need next-hop-self), split-horizon (can't readvertise iBGP routes to iBGP peers), requires full mesh or Route Reflectors, AD=200.

## Q4. BGP best-path selection algorithm (full order).

**Answer:** (1) Highest Weight (Cisco-local). (2) Highest LOCAL_PREF. (3) Locally originated. (4) Shortest AS_PATH. (5) Lowest Origin (IGP < EGP < Incomplete). (6) Lowest MED (same neighboring AS only). (7) eBGP over iBGP. (8) Lowest IGP metric to next-hop. (9) Oldest eBGP route. (10) Lowest Router ID. (11) Lowest neighbor IP. Mnemonic: "We Love Oranges AS Oranges Mean Pure Refreshment."

## Q5. What is LOCAL_PREF?

**Answer:** Tells iBGP routers which exit point to prefer. Higher = preferred. Default = 100. Only within the AS — never sent to eBGP peers. Example: ISP-A routes get LOCAL_PREF 200 (preferred), ISP-B gets 100 (backup).

```
route-map PREFER-ISP-A permit 10
  set local-preference 200
```

## Q6. What is MED?

**Answer:** Tells an external AS which entry point to prefer. Lower = preferred. Compared ONLY between routes from the same neighboring AS by default. `bgp always-compare-med` compares across ASes — use with caution.

## Q7. BGP Route Reflectors.

**Answer:** Solve iBGP full-mesh requirement. RR receives routes from clients and reflects them. Clients peer only with RR. Loop prevention: ORIGINATOR_ID (drop routes with own ID), CLUSTER_LIST (drop routes with own cluster-ID). Typically two RRs for redundancy.

```
router bgp 65001
  neighbor 10.0.0.2 route-reflector-client
```

## Q8. BGP Confederations vs Route Reflectors.

**Answer:** Confederations divide AS into sub-ASes, each running iBGP full mesh internally, confederation-eBGP between them. External world sees one AS. RRs are hierarchical (more common, simpler). Confederations are partitioned (useful for very large, geographically segmented networks). RR used in 95%+ of deployments.

## Q9. BGP Communities with practical examples.

**Answer:** 32-bit tags for policy signaling (AS:value). Well-known: NO_EXPORT, NO_ADVERTISE, LOCAL_AS. Practical: (1) Tag by origin (65001:1000 = ISP-A learned). (2) Blackhole (RTBH:666 to ISP for DDoS mitigation). (3) Traffic engineering (ISP-published communities for prepending control). Extended communities: VPN Route Targets. Large communities (RFC 8092): 96-bit for 4-byte ASNs.

## Q10. BGP route aggregation and ATOMIC_AGGREGATE.

**Answer:** Combine specific prefixes into summaries. `aggregate-address 10.1.0.0/22 summary-only` suppresses specifics. ATOMIC_AGGREGATE signals lost AS-PATH information in the aggregate. AGGREGATOR identifies who created it. `as-set` option preserves contributing AS-PATHs.

## Q11. BGP route dampening.

**Answer:** Suppresses flapping routes. Each flap adds penalty (1000). Exceeds suppress limit (2000) → route suppressed. Penalty decays with half-life (15min). Drops below reuse limit (750) → route unsuppressed. Controversial: delays legitimate convergence. Modern practice: most operators don't use it; rely on Graceful Restart/Shutdown instead.

## Q12. BGP Graceful Restart (RFC 4724).

**Answer:** Restarting router sets GR capability. Peers keep stale routes in RIB and forwarding table during restart timer (120s). Router re-establishes, re-sends routes, peers refresh. Data plane continues forwarding — zero traffic loss for planned restarts.

```
router bgp 65001
  bgp graceful-restart
  bgp graceful-restart restart-time 120
```

## Q13. AS-PATH prepending.

**Answer:** Adds own ASN multiple times to make path longer and less preferred. Inbound traffic engineering: prepend 3x on backup ISP advertisement. Caveats: only works if remote AS uses AS-PATH length, don't over-prepend (3-4x max), increases hijacking vulnerability.

```
route-map PREPEND-ISP-B permit 10
  set as-path prepend 65001 65001 65001
```

## Q14. BGP next-hop-self.

**Answer:** iBGP preserves the eBGP next-hop by default. If iBGP peers can't reach the eBGP peer IP, routes are unusable. `next-hop-self` rewrites next-hop to the border router's loopback (reachable via IGP). Nearly universal iBGP config.

## Q15. Soft reset vs hard reset.

**Answer:** Hard: tears down TCP session, full reconvergence, traffic disruption. Soft inbound: re-applies inbound policy to stored routes (needs `soft-reconfiguration inbound` or Route Refresh capability). Soft outbound: re-applies outbound policy and re-advertises. Route Refresh (RFC 2918): asks peer to re-send routes — preferred method, no stored copy needed.

```
clear bgp ipv4 unicast X.X.X.X soft in
clear bgp ipv4 unicast X.X.X.X soft out
```

## Q16. Prefix lists vs ACLs for route filtering.

**Answer:** Prefix lists match both network AND length (e.g., `10.0.0.0/8 le 24`). ACLs match network only, can't control mask. Prefix lists use trie (O(log n)), ACLs sequential (O(n)). Use prefix lists for BGP filtering.

## Q17. BGP hijacking and prevention.

**Answer:** Attacker announces prefix they don't own. Prevention: RPKI/ROA (cryptographic origin validation), IRR filtering, prefix lists, BGPsec (AS-PATH signing, limited deployment), max-prefix limits.

## Q18. RPKI and Route Origin Validation.

**Answer:** RIRs sign ROAs binding prefix → authorized origin AS. Validator (Routinator) fetches ROAs via RPKI trust anchors, feeds router via RTR protocol. States: Valid (ROA matches), Invalid (AS mismatch → drop), NotFound (no ROA → accept cautiously).

## Q19. BFD with BGP.

**Answer:** BFD detects link failure in 50-300ms. BGP hold timer default is 180s — too slow. BFD: peers exchange small UDP packets at high frequency, declare down after 3 missed packets. BGP tears down session immediately. Convergence <1 second.

```
router bgp 65001
  neighbor 10.0.0.2 fall-over bfd
interface GigabitEthernet0/0
  bfd interval 100 min_rx 100 multiplier 3
```

## Q20. BGP in spine-leaf DC fabric (RFC 7938).

**Answer:** Each device gets unique ASN. Leaves peer with all spines via eBGP. No iBGP, no RR, no full mesh. Advantages: no flooding (targeted UPDATEs vs OSPF LSA flood), better policy control, natural ECMP across spines, fast convergence with BFD.

## Q21. network vs redistribute in BGP.

**Answer:** `network` explicitly advertises a prefix already in the RIB. Precise, controlled. Origin = IGP (i). `redistribute` imports from another protocol. Broader, riskier. Origin = Incomplete (?). Use `network` for eBGP; `redistribute` carefully with route-maps.

## Q22. 4-byte ASN.

**Answer:** RFC 6793. 2-byte ASNs (1-65535) running out. 4-byte: up to 4294967295. Notation: asdot (65001.1) or asplain (4259841). Legacy routers see AS_TRANS (23456). Private range: 4200000000-4294967294.

## Q23. BGP ADD-PATH.

**Answer:** RFC 7911. Advertises multiple paths per prefix (each with Path ID). Benefits: faster convergence (backup paths pre-installed), better ECMP, eliminates RR path-hiding.

## Q24. Long-Lived Graceful Restart (LLGR).

**Answer:** Extends stale route retention to hours/days. Stale routes tagged LLGR_STALE with lowest priority. Use case: satellite/remote links with extended maintenance.

## Q25. Route filtering comparison.

**Answer:** Prefix-lists: match prefix + length. AS-PATH ACLs: match AS-PATH via regex. Route-maps: combine both + set actions (LOCAL_PREF, MED, community, next-hop). Use route-maps for complex policy; prefix-lists for simple filtering.

## Q26. BGP Flowspec (RFC 5575).

**Answer:** Distributes traffic filtering rules via BGP UPDATEs. Match on src/dst IP, protocol, port, packet length, TCP flags. Actions: rate-limit, drop, redirect, mark DSCP. Use case: DDoS mitigation — inject rule, propagates to all edge routers in seconds.

## Q27. Troubleshooting BGP stuck in Active.

**Answer:** Active = TCP failing. Checks: (1) Ping neighbor IP. (2) TCP 179 blocked? Verify ACLs both sides. (3) Correct neighbor IP configured? (4) update-source configured for loopback peering? (5) ebgp-multihop if not directly connected? (6) MD5 key mismatch? `debug ip bgp` for details.

```
show bgp neighbors <ip> | include state|last reset
show ip route <neighbor-ip>
```

## Q28. BGP looking glass for troubleshooting.

**Answer:** Public web interfaces to query an ISP's BGP table externally. Verify prefix visibility, AS-PATH, prepending effectiveness, detect blackholing. Major LGs: RIPE RIS, RouteViews, he.net/bgp.

## Q29. Dual-homed enterprise with two ISPs.

**Answer:** Inbound: prepend on backup ISP. Outbound: LOCAL_PREF 200 for primary, 100 for backup. Failover: primary link fails → BFD detects → routes withdrawn → backup takes over. ECMP if both paths equal (`maximum-paths 2`).

## Q30. Full BGP table size and implications.

**Answer:** ~1M+ IPv4 prefixes, ~200K IPv6. Needs 2-4GB RIB memory. TCAM on switches: 512K-1M routes (Nexus 9000). FIB overflow → CPU forwarding (catastrophic). If not transit provider, take default + partial routes instead of full table.

## Q31. eBGP multihop and GTSM.

**Answer:** eBGP TTL=1 default. `ebgp-multihop` increases TTL for non-direct peering (loopback, through firewall). Security: GTSM (`ttl-security hops 1`) accepts only TTL=255 packets — rejects spoofed packets from remote networks.

## Q32. Multiprotocol BGP (MP-BGP).

**Answer:** RFC 4760. Address families: IPv4 Unicast, IPv6 Unicast, VPNv4 (MPLS L3VPN), VPNv6, L2VPN EVPN (DC VXLAN), Flowspec. Each activated independently under BGP process.

## Q33. EVPN route types.

**Answer:** Type 2: MAC/IP advertisement. Type 3: Inclusive Multicast (BUM handling). Type 5: IP prefix (L3 inter-VNI routing). Type 1/4: multi-homing (ESI-based). EVPN replaces flood-and-learn with BGP-based MAC distribution.

## Q34. RTBH (Remotely Triggered Black Hole).

**Answer:** Trigger router advertises /32 with community (65001:666) and next-hop pointing to Null0. Edge routers match community, set next-hop to Null0, drop traffic at ingress. Lift by withdrawing the /32.

## Q35. BGP session security.

**Answer:** MD5 (RFC 2385, weak but common), TCP-AO (RFC 5925, stronger, key rotation), GTSM (RFC 5082, TTL-based spoofing prevention), prefix-lists (limit accepted prefixes), max-prefix limits (tear down on leak).

```
neighbor 10.0.0.2 password s3cur3Key
neighbor 10.0.0.2 ttl-security hops 1
neighbor 10.0.0.2 maximum-prefix 100 80
```

## Q36. BGP Conditional Advertisement.

**Answer:** Advertise a route only when a condition is met. `advertise-map` + `non-exist-map`: advertise backup prefix only when primary route disappears. Used for controlled failover to backup ISP.

## Q37. Optimal Route Reflection (ORR).

**Answer:** Standard RR selects best path from its own perspective. ORR (RFC 9107) calculates best path from each client's perspective using client's IGP metrics. Prevents suboptimal routing caused by RR's location.

## Q38. BGP ECMP and multipath.

**Answer:** `maximum-paths N` for eBGP, `maximum-paths ibgp N` for iBGP. Paths must have same AS-PATH length (relaxed with `bgp bestpath as-path multipath-relax`). Enables load balancing across multiple BGP paths.

## Q39. BGP PIC (Prefix Independent Convergence).

**Answer:** Pre-computes backup paths. Primary fails → FIB switches to backup in ~50ms without recalculating all prefixes. Critical for large tables (1M+ routes would take seconds to reconverge otherwise).

## Q40. BGP Monitoring Protocol (BMP).

**Answer:** RFC 7854. Streams BGP messages (Adj-RIB-In, Adj-RIB-Out, Loc-RIB) to monitoring station in real-time. Used for traffic engineering analysis, security monitoring, route analytics.

## Q41. BGP Extended Communities.

**Answer:** 64-bit. Route Targets (RT) for VPN import/export. Site of Origin (SoO) prevents loops in multi-homed CE. Color communities for SR-TE policy steering.

## Q42. BGP Graceful Shutdown (RFC 8326).

**Answer:** GRACEFUL_SHUTDOWN community (65535:0) set before maintenance. Peers reduce LOCAL_PREF to 0, traffic shifts to alternates BEFORE session drops. Zero-downtime maintenance.

## Q43. BGP Large Communities (RFC 8092).

**Answer:** 96-bit: GlobalAdmin:LocalData1:LocalData2. Needed for 4-byte ASNs which can't fit in standard 32-bit community AS field.

## Q44. BGP Unnumbered (RFC 5549).

**Answer:** eBGP over IPv6 link-local addresses, exchanging IPv4 routes. No IPv4 needed on inter-switch links. Simplifies DC fabric IP management.

## Q45. BGP Dynamic Neighbors.

**Answer:** `bgp listen range 10.0.0.0/24 peer-group LEAVES` — accept sessions from any peer in range. Used in DC fabrics with dynamically provisioned leaf switches.

## Q46. BGP and SD-WAN interaction.

**Answer:** OMP (Overlay Management Protocol) redistributes routes to/from BGP at WAN edge. CE routers peer via eBGP with SD-WAN edge. OMP carries TLOC attributes that BGP doesn't understand — translation at redistribution point.

## Q47. BGP route dampening parameters.

**Answer:** Suppress limit (default 2000), reuse limit (750), half-life (15min), max-suppress-time (60min). Tuning: lower half-life = faster recovery but more flap sensitivity. RFC 7196 recommends conservative parameters.

## Q48. BGP path attributes classification.

**Answer:** Well-known mandatory (ORIGIN, AS_PATH, NEXT_HOP). Well-known discretionary (LOCAL_PREF, ATOMIC_AGGREGATE). Optional transitive (COMMUNITY, AGGREGATOR). Optional non-transitive (MED, ORIGINATOR_ID, CLUSTER_LIST).

## Q49. iBGP next-hop resolution.

**Answer:** iBGP next-hop must be reachable via IGP (OSPF/IS-IS). If next-hop not in IGP → route unusable. Solutions: next-hop-self, redistribute eBGP peer IPs into IGP (bad practice), recursive lookup with IGP route covering the next-hop.

## Q50. Design: BGP-based Anycast DNS.

**Answer:** Each DNS node advertises same /32 via eBGP. Nodes in multiple cities attract local queries. Health-check daemon withdraws BGP route on DNS failure (ExaBGP + script). ECMP distributes across local nodes. Consistent hashing for TCP session persistence.


\newpage

# SECTION 3: OSPF (50 Questions)

## Q1. What type of protocol is OSPF? Explain link-state operation.

**Answer:** OSPF is a link-state IGP. Each router discovers neighbors (Hello), builds adjacencies, exchanges LSAs describing its links, stores all LSAs in the LSDB (identical within area), runs Dijkstra's SPF to compute shortest path tree, installs routes. Loop-free by design (complete topology map). Protocol 89 over IP. AD=110.

## Q2. OSPF area types.

**Answer:** **Normal:** All LSA types. **Stub:** No Type-5 externals, ABR injects default. **Totally Stubby:** No Type-3/4/5, only default. **NSSA:** Stub but allows local external routes (Type-7, converted to Type-5 at ABR). **Totally NSSA:** Totally Stubby + NSSA.

```
area 1 stub                    ! Stub
area 2 stub no-summary         ! Totally stubby
area 3 nssa                    ! NSSA
area 4 nssa no-summary         ! Totally NSSA
```

## Q3. All OSPF LSA types.

**Answer:** Type 1 (Router): every router's interfaces/neighbors, area-scoped. Type 2 (Network): DR-generated, lists attached routers on multi-access segment. Type 3 (Summary): ABR-generated, inter-area routes. Type 4 (ASBR Summary): ABR tells how to reach ASBR. Type 5 (External): ASBR-generated, redistributed routes, flooded everywhere except stubs. Type 7 (NSSA External): like Type 5 but within NSSA, converted at ABR.

```
show ip ospf database            # Full LSDB
show ip ospf database external   # Type 5
```

## Q4. OSPF neighbor states and adjacency formation.

**Answer:** Down → Init (Hello received, one-way) → 2-Way (bidirectional, DR/BDR election here) → ExStart (master/slave for DBD) → Exchange (DBD packets) → Loading (LSR/LSU for missing LSAs) → Full. Stuck in Init = one-way (ACL). Stuck in ExStart/Exchange = MTU mismatch (most common). 2-Way for DROTHER-to-DROTHER = normal.

## Q5. DR/BDR election.

**Answer:** On multi-access networks, reduces adjacencies from O(n²) to O(n). All routers peer with DR and BDR only. Highest priority wins (default 1, range 0-255, 0=never DR). Tie: highest Router ID. Non-preemptive — later higher-priority router doesn't take over until DR fails.

## Q6. OSPF timers and mismatch impact.

**Answer:** Hello: 10s (broadcast), 30s (NBMA). Dead: 4x Hello. Hello and Dead must match — mismatch prevents adjacency. SPF throttling: `timers throttle spf 1 50 5000`.

## Q7. OSPF route summarization.

**Answer:** Only at ABRs (inter-area: `area X range`) and ASBRs (external: `summary-address`). Reduces table size, limits SPF scope, provides stability. Null0 route auto-installed to prevent loops.

## Q8. Virtual links.

**Answer:** Extend Area 0 through a transit area when an area can't physically connect to backbone. Configured on both ABRs. Transit area can't be stub. Workaround, not design goal — replace with proper connectivity when possible.

## Q9. OSPF authentication.

**Answer:** Type 0 (null), Type 1 (plaintext — avoid), Type 2 (MD5/SHA HMAC — key never sent on wire). Key ID enables rotation. Area-level: `area 0 authentication message-digest`.

## Q10. OSPF vs IS-IS.

**Answer:** Both link-state, SPF-based. OSPF over IP, IS-IS over L2. IS-IS has flatter area model (L1/L2), TLV-based encoding (easy extension), slightly faster convergence. Choose IS-IS for large SP/DC networks. Choose OSPF for enterprise campus (better Cisco tooling, operator familiarity).

## Q11-Q50 (Condensed):

**Q11:** Network types — Broadcast, Point-to-Point, NBMA, Point-to-Multipoint. **Q12:** OSPFv3 — runs over IPv6 link-local, IPsec auth, instance ID. **Q13:** Stub router — `max-metric router-lsa` makes router last-resort transit. **Q14:** Fast convergence — BFD + SPF timer tuning. **Q15:** Redistribution — use route-maps with tags to prevent loops, set metric type (E1 adds internal cost, E2 fixed). **Q16:** Cost = reference-BW / interface-BW. Fix: `auto-cost reference-bandwidth 100000`. **Q17:** Prefix suppression — hides transit /30s. **Q18:** Demand circuits — suppress periodic Hellos on expensive links. **Q19:** Graceful restart (RFC 3623). **Q20:** LSDB overload — `max-lsa` limits accepted LSAs.

**Q21:** Multi-area adjacency. **Q22:** NSSA translator election (highest RID). **Q23:** Loop prevention in redistribution (tags). **Q24:** OSPF over GRE (recursive routing caveat). **Q25:** Sham links for MPLS L3VPN. **Q26:** Routers per area (<50 best practice). **Q27:** ABR placement at aggregation boundaries. **Q28:** Summarization strategy at ABRs. **Q29:** OSPF in hub-spoke DMVPN. **Q30:** Convergence in 500-router network.

**Q31-Q40 Troubleshooting:** Q31: ExStart stuck = MTU mismatch. Q32: Missing routes = area config, filter lists. Q33: Asymmetric routing = cost mismatch. Q34: SPF storms = flapping interface. Q35: No externals in stub = by design. Q36: DR election wrong = non-preemptive. Q37: No neighbors = hello/dead/area/auth/subnet mismatch. Q38: LSDB full = redistribution loop. Q39: High CPU = SPF instability. Q40: No IA routes in totally stubby = by design.

**Q41-Q50 Advanced:** Q41: OSPF with VRF-Lite. Q42: Segment Routing with OSPF. Q43: Graceful maintenance (max-metric drain). Q44: Multi-vendor interop. Q45: ECMP (maximum-paths). Q46: Transit area can't be stub for virtual links. Q47: Forward address in Type-5 LSAs. Q48: distribute-list filters RIB not LSDB. Q49: ABR = interfaces in 2+ areas including Area 0. Q50: Multi-site OSPF over MPLS design.

\newpage

# SECTION 4: LINUX NETWORKING (50 Questions)

## Q1. Network namespaces.

**Answer:** Isolated copy of the network stack — own interfaces, routing, iptables, ARP, sockets. Containers run in separate namespaces. Connected via veth pairs.

```
ip netns add test_ns
ip netns exec test_ns ip addr show
ip netns list
```

## Q2. Veth pairs.

**Answer:** Two virtual interfaces connected like a pipe. One end in container (eth0), other in host (vethXXX).

```
ip link add veth-host type veth peer name veth-ns
ip link set veth-ns netns test_ns
ip addr add 10.0.0.1/24 dev veth-host
ip netns exec test_ns ip addr add 10.0.0.2/24 dev veth-ns
ip link set veth-host up
ip netns exec test_ns ip link set veth-ns up
```

## Q3. iptables chains and tables.

**Answer:** 5 tables (raw, mangle, nat, filter, security), 5 chains (PREROUTING, INPUT, FORWARD, OUTPUT, POSTROUTING). Incoming-local: PREROUTING→INPUT. Forwarded: PREROUTING→FORWARD→POSTROUTING. Local-originated: OUTPUT→POSTROUTING. filter=accept/drop, nat=DNAT/SNAT, mangle=modify headers.

```
iptables -t nat -L -n -v
iptables-save
```

## Q4. Conntrack (connection tracking).

**Answer:** Tracks connection state for stateful firewalling and NAT. States: NEW, ESTABLISHED, RELATED, INVALID. NAT depends on conntrack for reverse translation. At scale: tune `nf_conntrack_max` (default 65536-262144).

```
conntrack -L       # List tracked connections
conntrack -C       # Count
sysctl net.netfilter.nf_conntrack_max
```

## Q5. IPVS vs iptables for load balancing.

**Answer:** IPVS: hash-based O(1), multiple algorithms (rr, lc, sh, wrr, wlc, sed, nq), handles 10K+ virtual servers. iptables: sequential O(n), probability-based random selection. kube-proxy IPVS mode creates virtual server per ClusterIP.

```
ipvsadm -Ln          # Virtual/real servers
ipvsadm -Ln --stats  # Traffic stats
```

## Q6-Q50 (Condensed):

**Q6:** Linux bridge — `ip link add br0 type bridge`. STP, VLAN filtering support. **Q7:** Policy routing — `ip rule add from 10.0.1.0/24 table 100`. **Q8:** TUN/TAP — TUN=L3, TAP=L2. VPN software. **Q9:** VXLAN on Linux — `ip link add vxlan0 type vxlan id 42 remote X dstport 4789`. **Q10:** XDP — eBPF at NIC driver, before skb. XDP_DROP for DDoS at line rate.

**Q11:** tc (traffic control) — rate limiting, shaping, Cilium eBPF hooks. **Q12:** ip vs ifconfig — always use `ip` (iproute2). **Q13:** ss vs netstat — `ss -tlnp` faster, reads from kernel directly. **Q14:** tcpdump — `tcpdump -i eth0 -nn port 80 -w capture.pcap`. **Q15:** nftables — replaces iptables, unified framework.

**Q16:** Network bonding — mode 4 (802.3ad/LACP) most common. **Q17:** MTU/PMTUD — ICMP "fragmentation needed" blocked = hanging connections. Fix: `--clamp-mss-to-pmtu`. **Q18:** ARP — `ip neigh show`. **Q19:** /proc/sys/net tuning — ip_forward, somaxconn, tcp_tw_reuse, conntrack_max, rmem/wmem. **Q20:** systemd-networkd vs NetworkManager.

**Q21:** DNS resolution — resolv.conf, systemd-resolved, nsswitch.conf. **Q22:** Firewalld vs raw iptables. **Q23:** Performance tuning — ring buffers, RSS/RPS, interrupt coalescing, TCP BBR. **Q24:** WireGuard — kernel-native VPN, Curve25519 + ChaCha20-Poly1305. **Q25:** Troubleshooting workflow — ip addr → ip route → ss → ping/traceroute → tcpdump → iptables → conntrack → ethtool → dmesg.

**Q26-Q50:** Policy routing details. ebtables. macvlan/ipvlan. Persistent netns. /sys/class/net. ethtool diagnostics. iperf3 bandwidth testing. mtr real-time traceroute. nmap. TCP stack internals (SYN/accept queue). BBR vs Cubic. SO_REUSEPORT. eBPF reinforced. systemd socket activation. sysctl hardening. VLAN tagging (8021q). GRE tunnels. IPv6 (SLAAC, privacy extensions). DPDK userspace networking. AF_PACKET raw sockets. PXE boot. Linux as router (FRRouting). Netfilter hooks. cgroup bandwidth limiting. DNS troubleshooting (dig +trace, strace).


\newpage

# SECTION 5: SWITCHING — VLAN, STP, RSTP, ETHERCHANNEL, VTP (50 Questions)

## Q1. What is a VLAN?

**Answer:** Logical segmentation of a switch into multiple broadcast domains. Limits broadcast scope, improves security, enables logical grouping regardless of physical location. Each VLAN requires L3 device (router or SVI) for inter-VLAN routing.

## Q2. STP (802.1D) vs RSTP (802.1w).

**Answer:** STP: 30-50s convergence (Listening→Learning→Forwarding). RSTP: sub-second. Key improvements: Alternate/Backup port roles for instant failover, Discarding state (combines Blocking+Listening), Proposal/Agreement for rapid transition on P2P links, edge ports transition immediately.

## Q3. EtherChannel and negotiation protocols.

**Answer:** Bundles physical links into one logical link. **LACP (802.3ad):** Active/Passive. Open standard. **PAgP (Cisco):** Desirable/Auto. **Static (On):** No negotiation, risky. Load balancing via header hash (src-dst-ip most common).

```
interface range Gi0/1 - 4
  channel-group 1 mode active
```

## Q4. VTP risks.

**Answer:** VTP Server creates VLANs, propagates via revision number. A lab switch with higher revision connected to production overwrites the VLAN database — catastrophic. Mitigation: VTP Transparent mode, VTP passwords, VTPv3 primary server concept, or disable VTP entirely.

## Q5. Root Bridge election.

**Answer:** Lowest Bridge ID (Priority + MAC). Default priority=32768. Non-preemptive. Control: `spanning-tree vlan X priority 4096` on desired root. Root should be the most capable switch (core/distribution).

## Q6. BPDU Guard.

**Answer:** Shuts port on ANY BPDU reception. For access ports (portfast). Prevents rogue switches/VMs from causing STP topology changes.

```
spanning-tree portfast default
spanning-tree portfast bpdu-guard default
```

## Q7. Root Guard vs BPDU Guard.

**Answer:** Root Guard blocks only SUPERIOR BPDUs (prevents Root Bridge change). Port goes root-inconsistent, recovers when BPDUs stop. For switch-to-switch ports. BPDU Guard shuts on ANY BPDU — for end-user ports.

## Q8. 802.1Q and native VLAN security.

**Answer:** 802.1Q inserts 4-byte tag. Native VLAN frames sent untagged. VLAN hopping: double-tagging exploits native VLAN. Fix: change native to unused VLAN, tag native explicitly, don't use VLAN 1.

## Q9. Private VLANs.

**Answer:** L2 isolation within a VLAN. Promiscuous (talks to all — gateway), Isolated (only talks to promiscuous), Community (talks to promiscuous + same community). Use: hosting environments, multi-tenant with shared subnet.

## Q10. DHCP Snooping and DAI.

**Answer:** DHCP Snooping: trusted ports accept DHCP offers, untrusted only requests. Builds binding table (MAC→IP→VLAN→port). DAI (Dynamic ARP Inspection): validates ARP against binding table. Prevents rogue DHCP and ARP spoofing.

```
ip dhcp snooping
ip dhcp snooping vlan 10,20,30
ip arp inspection vlan 10,20,30
```

## Q11-Q50 (Condensed):

**Q11-20:** MSTP (multiple VLANs per STP instance). LACP fast timers. EtherChannel misconfiguration. Storm control. Port security. SPAN/RSPAN/ERSPAN. UDLD. StackWise/VSS. Loop Guard. VLAN Access Maps.

**Q21-30:** Troubleshooting: MAC flapping, STP loops, trunk negotiation failures, VLAN mismatch, native VLAN mismatch, EtherChannel load imbalance, err-disabled recovery, root bridge instability, unidirectional link detection, broadcast storms.

**Q31-40:** Design: campus access/distribution/core, inter-VLAN routing (router-on-a-stick vs SVI), VLAN sprawl management, QoS at access layer, voice VLAN, L3 routed access (eliminating STP), multi-site VLAN extension (should you?), VLAN naming conventions, management VLAN best practices, wireless VLAN design.

**Q41-50:** Advanced: MACsec (802.1AE). 802.1X with RADIUS. Dynamic VLAN assignment. Cisco TrustSec/SGT. Fabric technologies replacing STP. PVST+ vs RPVST+. STP topology change mechanism. Spanning-tree pathcost method (short vs long). Spanning-tree dispute mechanism. Troubleshooting exercise: identify root cause from show spanning-tree output.

\newpage

# SECTION 6: DATA CENTER TECHNOLOGIES (50 Questions)

## Q1. Spine-leaf (Clos) architecture.

**Answer:** Every leaf connects to every spine. No leaf-leaf or spine-spine links. 2 hops between any servers (leaf→spine→leaf). Predictable latency, ECMP across all spines, no STP, horizontal scaling. Routing: eBGP (RFC 7938) or OSPF/IS-IS.

## Q2. VXLAN.

**Answer:** RFC 7348. Encapsulates L2 in UDP (port 4789). 24-bit VNI (16M segments vs 4094 VLANs). Extends L2 over L3 routed fabric. No STP. VTEP on each leaf handles encap/decap. Control plane: EVPN (BGP-based, preferred) or flood-and-learn.

## Q3. Cisco ACI.

**Answer:** SDN for DC. APIC (controller cluster) + Nexus 9000 spines/leaves. IS-IS underlay, VXLAN overlay. Object model: Tenant → VRF → Bridge Domain → EPG → Contract. Whitelist model: no traffic between EPGs without Contract.

## Q4-Q50 (Condensed):

**Q4-10:** EVPN-VXLAN (Type-2/3/5 routes). vPC (dual-switch LAG). FEX. Bare-metal vs overlay. DCI (OTV, VXLAN multi-site). East-west vs north-south. Micro-segmentation.

**Q11-20:** Server NIC bonding. QoS/lossless Ethernet (PFC, ECN). Storage networking (iSCSI, FC, FCoE). DC power/cooling. ToR vs MoR placement. Oversubscription ratios. Spine capacity planning. SDN controllers. NSX-T architecture. SmartNIC/DPU offload.

**Q21-30:** SONiC. Cumulus Linux. DC automation (Ansible, Terraform, Nornir). Day-0/1/2 operations. ZTP. GitOps for DC. EVPN Type-5 for inter-VNI L3. Asymmetric vs Symmetric IRB. Multi-tenancy in VXLAN. ACI vs standalone NX-OS comparison.

**Q31-40:** Troubleshooting: VXLAN tunnel failures, ACI contract misconfig, vPC peer-link issues, VTEP reachability, overlay/underlay diagnosis, MTU with VXLAN overhead, TCAM exhaustion, BUM storms, ARP suppression, spine failure impact analysis.

**Q41-50:** Design: 1000-server fabric, multi-site active-active, DR connectivity, legacy-to-spine-leaf migration, 400G spine planning, multi-tenant isolation, firewall placement (leaf vs spine vs service chain), monitoring strategy, capacity planning, brownfield vs greenfield DC network design.

\newpage

# SECTION 7: CLOUD NETWORKING — AZURE FOCUS (50 Questions)

## Q1. Azure VNet fundamentals.

**Answer:** VNet = isolated CIDR-defined address space. Subnet = subdivision (Azure reserves 5 IPs). NSG = stateful L4 firewall (subnet or NIC level). UDR = custom routing for traffic steering. VNet Peering = connects VNets (non-transitive). Service Tags = Azure-managed IP range labels.

## Q2. Azure Private Link and Private Endpoints.

**Answer:** Private access to PaaS (Storage, SQL) via private IP in your VNet. Private Endpoint = NIC with private IP mapped to PaaS resource. DNS must resolve PaaS FQDN to private IP (via Azure Private DNS Zone). Traffic stays on Microsoft backbone.

## Q3. Hub-and-spoke topology.

**Answer:** Hub VNet: shared services (Azure Firewall, VPN/ExpressRoute Gateway). Spoke VNets: workloads, peered to hub. Spokes can't talk directly (non-transitive peering). Traffic flows through hub firewall via UDRs. Centralized security and connectivity.

## Q4-Q50 (Condensed):

**Q4-10:** VPN Gateway (S2S IPsec, up to 10 Gbps, active-active). ExpressRoute (private dedicated, 50Mbps-100Gbps). Virtual WAN (managed hub-spoke). Azure DNS. Azure Load Balancer (L4). Application Gateway (L7, WAF). Front Door (global L7, CDN).

**Q11-20:** Azure Firewall Premium (TLS inspect, IDPS). DDoS Protection. Bastion. Network Watcher (flow logs, packet capture, next hop). Route Server (BGP with NVAs). AWS VPC comparison. Transit Gateway. GCP VPC. Multi-cloud networking. Cloud vs traditional security groups.

**Q21-30:** Hybrid DNS. Service Endpoints vs Private Endpoints. NSG best practices. Cost optimization (cross-AZ charges). AKS networking (kubenet vs Azure CNI vs overlay). Azure Front Door vs Application Gateway. Azure NAT Gateway. Azure Virtual Network Manager. Forced tunneling. Azure Firewall Manager.

**Q31-40:** Troubleshooting: effective routes, NSG flow logs, VPN tunnel debug, ExpressRoute diagnostics, DNS failures, asymmetric routing in hub-spoke, UDR black holes, Private Endpoint DNS issues, peering connectivity, load balancer health probes.

**Q41-50:** Design: multi-region with DR, 50-spoke enterprise, dual ExpressRoute + VPN fallback, PCI-DSS compliant architecture, AKS networking with Calico, landing zone network design, Azure VMware Solution connectivity, cloud firewall vs NVA decision framework, network monitoring strategy, AZ-700 certification topics.


\newpage

# SECTION 8: ANSIBLE FOR NETWORK AUTOMATION (50 Questions)

## Q1. Why is Ansible preferred for network automation?

**Answer:** Agentless (network devices can't run agents — Ansible uses SSH/API). Idempotent (same playbook twice = same state). Declarative with resource modules. YAML-based (low barrier). Multi-vendor collections (Cisco, Arista, Juniper, Palo Alto, F5).

## Q2. cli_command vs resource modules.

**Answer:** `cli_command` is raw CLI — send commands, get text, parse yourself. Imperative. Resource modules (`cisco.ios.ios_interfaces`, `cisco.ios.ios_bgp_global`) are declarative — define desired state, module computes diff, applies only changes. Resource modules return structured data, support check_mode, are idempotent. Always prefer resource modules.

## Q3. assert for validation.

**Answer:** Pre/post-check gates. Validate device state before/after changes. Without assertions, playbooks push config blindly into degraded devices.

```yaml
- ansible.builtin.assert:
    that:
      - bgp_output.stdout[0] | regex_search('Established')
    fail_msg: "BGP NOT established — aborting"
```

## Q4. block/rescue/always pattern.

**Answer:** block: pre-check + change + post-check + validate. rescue: rollback on failure. always: capture final state regardless. This is the mandatory pattern for safe network automation — never push config without rollback capability.

## Q5-Q50 (Condensed):

**Q5-10:** Inventory (YAML, ansible_network_os, ansible_connection: network_cli). Vault for credentials. Jinja2 templates for config generation. Roles structure. cli_config vs ios_config. Facts gathering (gather_facts: false, ios_facts).

**Q11-20:** Idempotency challenges. Tags. Handlers for save-on-change. check_mode (dry run). diff mode. register + output parsing. Collections installation. Variable precedence (extra-vars wins). Loops for multi-device. Conditionals (when: ansible_network_os).

**Q21-30:** Serial execution (serial: 1 for rolling updates). Tower/AWX (scheduling, RBAC, logging). Dynamic inventory from NetBox/Nautobot. Config backup automation. Compliance checking. Network config diff with cli_command + assert. Error handling strategies. Performance tuning (forks, pipelining, persistent connections). Event-driven Ansible. CI/CD integration.

**Q31-40:** Practical playbooks: VLAN deployment across 50 switches, BGP neighbor config, NTP/syslog/SNMP baseline, ACL deployment with validation, firmware upgrade with pre/post checks, interface description standardization, OSPF rollout, user access management, cert rotation, DR automation.

**Q41-50:** Advanced: custom modules in Python, filters for network data, async for long commands, YANG/NETCONF with netconf_config, Batfish integration for pre-deployment validation, Ansible + Git workflow (MR triggers playbook), testing playbooks with Molecule, AWX API for programmatic execution, multi-vendor abstraction patterns, troubleshooting (-vvv, connection issues, SSH problems, timeout tuning).

\newpage

# SECTION 9: PYTHON FOR NETWORK AUTOMATION (50 Questions)

## Q1. Netmiko basics.

**Answer:**

```python
from netmiko import ConnectHandler

device = {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "secret",
}

with ConnectHandler(**device) as conn:
    output = conn.send_command("show ip route", use_textfsm=True)
```

Context manager ensures connection cleanup. `use_textfsm=True` returns structured data. `device_type` determines SSH timing and prompts.

## Q2. TextFSM parsing.

**Answer:** Template-based parser. NTC-Templates provides pre-built templates for 1000+ commands across vendors. Netmiko's `use_textfsm=True` auto-selects template. Returns list of dicts — each dict is one row (route, interface, neighbor).

## Q3. Netmiko vs NAPALM vs Nornir.

**Answer:** **Netmiko:** SSH library, low-level, send/receive. **NAPALM:** Abstraction layer — unified methods across vendors (get_interfaces, load_merge_candidate, commit_config, rollback). **Nornir:** Python-native framework (replaces Ansible for Python devs), inventory + concurrent task execution + result handling. Uses Netmiko/NAPALM as plugins.

## Q4. Exception handling.

**Answer:**

```python
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

try:
    with ConnectHandler(**device) as conn:
        output = conn.send_command(command, read_timeout=30)
except NetmikoTimeoutException:
    logger.error("Timeout: %s", device["host"])
except NetmikoAuthenticationException:
    logger.error("Auth failed: %s", device["host"])
except Exception:
    logger.exception("Unexpected error: %s", device["host"])
    raise
```

## Q5. Regex parsing.

**Answer:**

```python
import re
pattern = r'(\S+)\s+(\d+\.\d+\.\d+\.\d+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)'
for match in re.finditer(pattern, output):
    interfaces.append({
        "name": match.group(1),
        "ip": match.group(2),
        "status": match.group(3),
    })
```

For production, prefer TextFSM/TTP over manual regex.

## Q6-Q50 (Condensed):

**Q6-10:** REST API (requests + JSON), YANG/NETCONF (ncclient), async with scrapli (asyncio), type hints, dataclasses for device models.

**Q11-20:** Pydantic for config validation, structured logging (structlog), pathlib for files, Jinja2 templating in Python, unit testing (pytest + mock), NAPALM getters (get_facts/bgp_neighbors/route_to), NAPALM config management (load/compare/commit/rollback), Nornir inventory/tasks, PyATS/Genie (learn + diff).

**Q21-30:** SNMP (pysnmp), NetBox/Nautobot API (pynautobot/pynetbox), ThreadPoolExecutor for concurrency, env vars for secrets, CLI tools (click/typer), config backup with diff detection, BGP health checker script, interface utilization reporter, VLAN auditor (desired vs actual), ACL parser.

**Q31-40:** Network diagram generator (CDP/LLDP data), automated change window script, multi-vendor config standardizer, cert expiry checker, IPAM script with NetBox API, decorators for retry logic, context managers for connections, generators for streaming, abstract base classes for vendor abstraction, Strategy pattern for multi-vendor.

**Q41-50:** FastAPI for automation APIs, Celery for async queuing, Docker for automation tools, Rich for CLI output, Pandas for tabular analysis, Batfish for verification, Suzieq for observability, containerlab for lab automation, CI/CD pipeline integration, Python packaging (pyproject.toml, poetry) for reusable automation libraries.

\newpage

# COMMANDS QUICK REFERENCE

## Cisco IOS/IOS-XE

```
show ip route                             show ip bgp summary
show ip ospf neighbor                     show ip ospf database
show ip interface brief                   show interfaces status
show vlan brief                           show spanning-tree vlan <id>
show cdp neighbors detail                 show lldp neighbors detail
show etherchannel summary                 show port-channel summary
show crypto isakmp sa                     show crypto ipsec sa
show access-lists                         show ip nat translations
show running-config | section router bgp
show running-config | section router ospf
show logging                              show version
show processes cpu sorted
```

## Cisco NX-OS

```
show vpc brief                            show vpc peer-keepalive
show port-channel summary                 show nve peers
show nve vni                              show bgp l2vpn evpn
show l2route evpn mac all                 show fabric forwarding
feature vpc                               feature ospf
feature bgp                               feature interface-vlan
```

## Kubernetes

```
kubectl get pods -o wide
kubectl get svc -o wide
kubectl get networkpolicy -A
kubectl get endpointslice -l kubernetes.io/service-name=<svc>
kubectl -n kube-system get cm coredns -o yaml
kubectl exec -it <pod> -- nslookup kubernetes.default
kubectl exec -it <pod> -- cat /etc/resolv.conf
calicoctl node status
calicoctl get ippool -o yaml
calicoctl ipam show --show-blocks
cilium status
cilium service list
cilium bpf lb list
hubble observe --namespace <ns>
hubble observe --verdict DROPPED
```

## Linux Networking

```
ip addr show                              ip route show
ip link show type veth                    ip netns list
ip netns exec <ns> ip addr                ip rule show
ss -tlnp                                  ss -s
iptables -t nat -L -n -v                  iptables-save
ipvsadm -Ln                              conntrack -L
conntrack -C                              conntrack -D -d <ip>
tcpdump -i eth0 -nn port <port>           tcpdump -w cap.pcap
ethtool eth0                              ethtool -S eth0
sysctl net.ipv4.ip_forward
sysctl net.netfilter.nf_conntrack_max
sysctl net.netfilter.nf_conntrack_count
brctl show                                bridge fdb show
```

## Azure CLI

```
az network vnet list -o table
az network nsg list -o table
az network nsg rule list --nsg-name <nsg> -o table
az network vnet-gateway list -o table
az network vpn-connection list -o table
az network nic show-effective-route-table --name <nic> -g <rg>
az network watcher show-next-hop --vm <vm> --dest-ip <ip>
az network private-endpoint list -o table
az network vnet peering list --vnet-name <vnet> -g <rg> -o table
```

## Ansible

```
ansible-playbook site.yml -i inventory.yml
ansible-playbook site.yml --check --diff      # Dry run
ansible-playbook site.yml -vvv                # Debug
ansible-playbook site.yml --tags "bgp"        # Run tagged tasks only
ansible-vault encrypt secrets.yml
ansible-vault view secrets.yml
ansible-galaxy collection install cisco.ios
ansible-inventory --list -i inventory.yml
```

## Python/Automation

```bash
pip install netmiko napalm nornir pynapalm pynetbox
pip install textfsm ntc-templates
pip install scrapli scrapli-community
pip install pyats genie
python -m pytest tests/ -v                    # Run tests
python -m mypy src/ --strict                  # Type checking
```

---

\vfill
\begin{center}
\textbf{End of Interview Preparation Guide}\\
\textit{450 Questions · 9 Domains · Senior/Principal Level (8+ Years)}
\end{center}


\newpage

# OSPF EXPANDED ANSWERS (Q11-Q50)

## Q11. OSPF Network Types — explain each and when to use them.

**Answer:** **Broadcast (default on Ethernet):** DR/BDR election occurs. Hello 10s, Dead 40s. Multicast 224.0.0.5 (AllSPFRouters) and 224.0.0.6 (AllDRouters). Use on multi-access Ethernet segments. **Point-to-Point (default on serial/tunnel):** No DR/BDR. Only two routers. Hello 10s. Most efficient — full adjacency immediately. Use on P2P links, GRE tunnels. **NBMA (Non-Broadcast Multi-Access):** DR/BDR election. Hello 30s, Dead 120s. Manual neighbor statements required (no multicast). Use on Frame Relay, ATM (legacy). **Point-to-Multipoint:** No DR/BDR. Each neighbor treated as P2P adjacency. Hello 30s. Use on partial-mesh NBMA topologies (hub-and-spoke DMVPN). Mismatched network types between neighbors = adjacency failure.

```
interface GigabitEthernet0/0
  ip ospf network point-to-point    ! Override default broadcast
```

## Q12. OSPFv3 for IPv6.

**Answer:** Separate protocol from OSPFv2. Runs over IPv6 link-local addresses (fe80::). Uses IPsec for authentication instead of built-in MD5. Instance ID (0-255) allows multiple OSPF instances per link. Router ID is still 32-bit (configured manually or derived from IPv4). Address families carried in LSAs, not in the Hello. OSPFv3 can carry both IPv4 and IPv6 with Address Families (RFC 5838).

```
ipv6 router ospf 1
  router-id 1.1.1.1
interface GigabitEthernet0/0
  ipv6 ospf 1 area 0
```

## Q13. OSPF Stub Router (RFC 6987).

**Answer:** `max-metric router-lsa` advertises maximum metric (65535) on all links in the router's Type-1 LSA. Makes the router a last-resort transit path — other routers prefer any alternative. Use cases: (1) During boot: `max-metric router-lsa on-startup 300` — gives BGP 300 seconds to converge before the router carries transit traffic. (2) Pre-maintenance: set max-metric, wait for traffic to drain, then perform maintenance. (3) Graceful introduction/removal of routers from the network.

```
router ospf 1
  max-metric router-lsa on-startup 300
  max-metric router-lsa               ! Permanent max-metric
```

## Q14. OSPF Fast Convergence.

**Answer:** Default SPF timer has 5-second initial delay — unacceptable for production. Tuning: `timers throttle spf 1 50 5000` (1ms initial, 50ms between subsequent SPF runs, 5s max wait). LSA throttling: `timers throttle lsa all 0 50 5000`. BFD for sub-second link failure detection (100ms intervals, 3x multiplier = 300ms detection). Interface dampening (`dampening`) prevents SPF storms from flapping links. Fast Hello (sub-second): `ip ospf dead-interval minimal hello-multiplier 4` — sends Hellos every 250ms, Dead interval = 1 second. Use with caution — high CPU on large deployments.

## Q15. OSPF Redistribution.

**Answer:** Redistributing routes into OSPF creates Type-5 (or Type-7 in NSSA) external LSAs. Two metric types: **E1** — external cost PLUS internal OSPF cost to the ASBR. Preferred when multiple ASBRs redistribute the same destination — traffic takes the closest ASBR. **E2 (default)** — fixed external cost regardless of internal distance. Simpler but can cause suboptimal routing if multiple ASBRs exist.

**Loop prevention:** When redistributing between OSPF and another protocol (especially mutual redistribution OSPF↔EIGRP), use route tags. Set a tag on routes redistributed into OSPF, then deny routes with that tag when redistributing back.

```
router ospf 1
  redistribute bgp 65001 subnets route-map BGP-TO-OSPF metric-type 1
!
route-map BGP-TO-OSPF permit 10
  match ip address prefix-list ALLOWED-EXTERNALS
  set metric 100
  set tag 65001
route-map BGP-TO-OSPF deny 20
  match tag 100    ! Prevent routes that came FROM OSPF being re-injected
```

## Q16. OSPF Cost Calculation.

**Answer:** Cost = Reference Bandwidth / Interface Bandwidth. Default reference = 100 Mbps. Problem: GigE = 100/1000 = 0.1, rounded to 1. 10GE = 100/10000 = 0.01, rounded to 1. 100G = 1. OSPF cannot distinguish between GigE, 10G, and 100G links — all have cost 1. Fix: increase reference bandwidth on ALL routers in the area:

```
router ospf 1
  auto-cost reference-bandwidth 100000    ! 100 Gbps
```

Now: GigE = 100, 10G = 10, 40G = 2.5 (rounded to 2), 100G = 1. All routers in the area MUST use the same reference — mismatch causes inconsistent path selection.

## Q17. OSPF Prefix Suppression.

**Answer:** Transit link addresses (/30s, /31s between routers) are reachable via OSPF but rarely need to be destinations. `prefix-suppression` removes them from the routing table while keeping them in the LSDB for SPF calculation. Reduces routing table size by hundreds of entries in large networks without affecting reachability. Loopbacks and stub networks (server-facing subnets) are NOT suppressed.

```
router ospf 1
  prefix-suppression           ! Enable globally
interface Loopback0
  ip ospf prefix-suppression disable   ! Keep loopback reachable
```

## Q18. OSPF Demand Circuits (RFC 1793).

**Answer:** On expensive WAN links (satellite, ISDN), periodic Hellos and LSA refreshes (every 30 minutes) waste bandwidth. Demand circuits suppress periodic traffic — Hellos only sent at startup to form adjacency, LSAs refreshed only when topology changes. The DoNotAge (DNA) bit is set on LSAs learned over demand circuits to prevent their 30-minute refresh.

```
interface Serial0/0
  ip ospf demand-circuit
```

## Q19. OSPF Graceful Restart (RFC 3623).

**Answer:** Restarting router signals GR in its Hello. Neighbors enter helper mode — maintain adjacency and continue forwarding traffic using stale routes. After restart, the router re-synchronizes its LSDB. Data plane forwarding continues uninterrupted. Similar concept to BGP GR. Supported on Cisco, Juniper, Arista. Configuration:

```
router ospf 1
  nsf cisco                    ! Cisco NSF (Non-Stop Forwarding)
  nsf ietf                     ! IETF GR (RFC 3623)
```

## Q20. OSPF LSDB Overload Protection.

**Answer:** `max-lsa` limits the number of non-self-originated LSAs a router will accept. If exceeded, OSPF enters overload state — ignores new LSAs for a configurable period, then attempts recovery. Prevents rogue routers or redistribution loops from consuming all memory with thousands of LSAs.

```
router ospf 1
  max-lsa 12000 75 ignore-time 5 ignore-count 5 reset-time 10
  ! 75% warning threshold, ignore for 5 min, max 5 ignores, reset after 10 min
```

## Q21. OSPF Multi-Area Adjacency.

**Answer:** A single physical link participates in multiple OSPF areas simultaneously. The primary interface belongs to one area; a logical multi-area adjacency is configured for another area. Eliminates the need for a virtual link or separate physical connection to connect a non-backbone area through an ABR's single interface.

```
interface GigabitEthernet0/0
  ip address 10.0.0.1 255.255.255.252
  ip ospf 1 area 0
  ip ospf multi-area 1               ! Also participate in Area 1
```

## Q22. NSSA Translator Election.

**Answer:** When multiple ABRs serve an NSSA, only one should convert Type-7 LSAs to Type-5 (to avoid duplicate Type-5s in the backbone). The ABR with the highest Router ID is elected as the translator. If the elected translator becomes unreachable, the next-highest Router ID ABR takes over. The translator sets the P-bit (Propagate) in the Type-7 LSA header to indicate it will be translated.

## Q23. Loop Prevention in Redistribution.

**Answer:** Mutual redistribution (OSPF ↔ EIGRP, OSPF ↔ BGP) creates the risk of routing loops — routes redistributed OUT of OSPF can be redistributed back IN. Prevention: (1) Tag routes at redistribution points. (2) Filter on the return path — deny routes with the tag you set. (3) Use distribute-lists to be explicit about which routes cross protocol boundaries.

```
route-map OSPF-TO-EIGRP permit 10
  set tag 100
route-map EIGRP-TO-OSPF deny 10
  match tag 100                      ! Block routes that came from OSPF
route-map EIGRP-TO-OSPF permit 20   ! Allow everything else
```

## Q24. OSPF over GRE Tunnels.

**Answer:** OSPF can run over GRE tunnels — the tunnel interface is assigned to an OSPF area as a point-to-point link. Considerations: (1) **Recursive routing:** If the route to the tunnel destination is learned via OSPF through the tunnel itself, the tunnel goes down (destination unreachable → tunnel down → route lost → repeat). Fix: static route to the tunnel destination. (2) **MTU:** GRE adds 24 bytes overhead. Set `ip mtu 1476` on the tunnel interface (1500 - 24). (3) **Bandwidth:** Tunnel interface default bandwidth is 9 Kbps on some platforms — set it correctly or OSPF cost will be astronomical.

## Q25. OSPF Sham Link.

**Answer:** In MPLS L3VPN, CE routers at two sites may have a backdoor link running OSPF. Without a sham link, OSPF prefers the backdoor (intra-area, lower cost) over the MPLS path (inter-area via MP-BGP). A sham link creates an intra-area OSPF adjacency between PE routers across the MPLS core, making the VPN path appear as intra-area. The sham link's cost is set lower than the backdoor's cost to prefer the MPLS path.

```
router ospf 1 vrf CUSTOMER
  area 0 sham-link 10.255.1.1 10.255.2.2 cost 5
```

## Q26. How many routers per OSPF area?

**Answer:** Best practice: fewer than 50 routers per area. SPF complexity is O(N log N) where N is the number of nodes in the area. With 50 routers and modest link density, SPF runs in single-digit milliseconds. At 200+ routers, SPF can take tens of milliseconds, and every topology change triggers recalculation for all routers in the area. More importantly, the LSDB size grows with router count, consuming memory.

## Q27. ABR placement strategy.

**Answer:** Place ABRs at natural aggregation boundaries — building edge, floor aggregation, campus core. Each ABR should serve as the summarization point. Design principle: areas should be contiguous and geographically or functionally coherent. Avoid areas that span long distances (WAN) — a link flap in one continent triggers SPF in routers on another continent within the same area.

## Q28. Route summarization strategy.

**Answer:** Design IP addressing hierarchically so summarization is clean. Example: Site A uses 10.1.0.0/16, Site B uses 10.2.0.0/16. ABR for Site A: `area 1 range 10.1.0.0 255.255.0.0`. A /24 flap in Site A generates a new Type-3 summary only if the /16 aggregate is affected (it isn't — the summary already covers it). This isolates instability.

## Q29. OSPF in hub-and-spoke DMVPN.

**Answer:** **Point-to-Multipoint (recommended):** No DR/BDR election (avoids issues with spokes being DR). Hub router is next-hop for all traffic (correct in hub-and-spoke). Each spoke-to-hub is treated as a separate P2P adjacency. **NBMA:** Requires manual neighbor statements on the hub. DR/BDR election — ensure hub is DR (set priority 0 on spokes). More complex, no advantage over P2P-multipoint in most DMVPN designs.

## Q30. Convergence optimization in a 500-router network.

**Answer:** (1) Area design: split into 8-10 areas of ~50 routers each. (2) Summarize aggressively at ABRs. (3) BFD on all links (100ms detect). (4) SPF timers: `timers throttle spf 1 50 5000`. (5) LSA throttling: `timers throttle lsa all 0 50 5000`. (6) Prefix suppression to reduce routing table churn. (7) Stub/Totally Stubby areas where external routes aren't needed. (8) Graceful Restart for planned maintenance. (9) max-metric for graceful introduction of new routers.

## Q31. Troubleshooting: neighbor stuck in EXSTART.

**Answer:** Almost always MTU mismatch. During EXSTART, routers exchange DBD (Database Description) packets. If one side has MTU 1500 and the other 9000 (jumbo frames), the larger DBD packets are dropped. Router keeps retransmitting DBD, stuck in EXSTART. Fix: ensure MTU matches on both sides. Verify: `show ip ospf interface <intf>` shows MTU. If MTU can't be changed, `ip ospf mtu-ignore` (workaround, not recommended — hides real MTU issues).

```
show ip ospf interface GigabitEthernet0/0 | include MTU
debug ip ospf adj
```

## Q32. Troubleshooting: routes missing from routing table.

**Answer:** Check: (1) Is the route in the LSDB? `show ip ospf database` — if not, the LSA isn't reaching this router (area config, filter). (2) Is the route being filtered? `show ip ospf database summary` for Type-3, check ABR's `area range` or distribute-list. (3) Is the area type blocking it? Stub/Totally Stubby blocks external/inter-area routes. (4) Is there a better route from another protocol? Check AD — EIGRP (90) beats OSPF (110).

## Q33. Troubleshooting: asymmetric routing.

**Answer:** OSPF cost mismatch on redundant paths. Example: Link A has cost 10, Link B has cost 100. Forward path takes Link A, return path takes Link B (because the remote router's costs are reversed). Fix: ensure costs are symmetric. `show ip ospf interface brief` on both routers — compare costs. Common cause: interface bandwidth not set correctly, or `auto-cost reference-bandwidth` differs between routers.

## Q34. Troubleshooting: SPF running too frequently.

**Answer:** `show ip ospf statistics detail` — shows SPF run history with timestamps and triggers. Common causes: flapping interface (link up/down/up every few seconds → new Type-1 LSA → SPF), redistribution instability (external route flapping → Type-5 LSA changes), or a neighbor that keeps forming/breaking adjacency (authentication issue, MTU issue causing intermittent failures). Fix the root cause, then tune SPF throttling as a safety net.

## Q35. No external routes in stub area.

**Answer:** By design. Stub areas filter Type-5 LSAs. The ABR injects a default route (Type-3 with 0.0.0.0/0). If you need external routes in the area, don't make it stub. If you need SOME external routes (from a local ASBR), use NSSA — it allows Type-7 LSAs from the local ASBR while still blocking Type-5s from other areas.

## Q36. DR election not matching expectation.

**Answer:** DR election is non-preemptive. If Switch A (priority 200) boots after Switch B (priority 100) has already become DR, Switch B remains DR. To force the desired DR: (1) Set priorities correctly. (2) Restart OSPF on both routers (`clear ip ospf process`) to trigger re-election. (3) In new deployments, bring up the intended DR first.

## Q37. No OSPF neighbors forming.

**Answer:** Checklist — ALL must match: (1) Hello/Dead interval. (2) Area ID. (3) Authentication type and key. (4) Subnet — both interfaces must be on the same IP subnet. (5) Network type. (6) Stub area flag (both sides must agree). (7) MTU (for adjacency formation beyond 2-Way). (8) ACL not blocking protocol 89 or multicast 224.0.0.5/6. (9) Interface not passive (`passive-interface`).

```
show ip ospf interface brief
show ip ospf neighbor
debug ip ospf hello
debug ip ospf adj
```

## Q38. OSPF database full / excessive LSAs.

**Answer:** Usually a redistribution loop or uncontrolled redistribution. Example: redistributing the entire BGP table (900K+ routes) into OSPF creates 900K Type-5 LSAs — every router in every non-stub area stores all of them. Fix: filter redistribution with prefix-lists/route-maps. Only redistribute what's needed. Use `max-lsa` as protection.

## Q39. High CPU due to OSPF.

**Answer:** `show processes cpu sorted | include OSPF` — identify which OSPF process. `show ip ospf statistics detail` — frequency and cause of SPF runs. Common causes: SPF running every few seconds due to instability (see Q34), large LSDB requiring significant computation, excessive LSA flooding from redistribution. Fix the instability, reduce LSDB size via area design, tune timers.

## Q40. Inter-area routes missing in totally stubby area.

**Answer:** By design. Totally stubby (stub no-summary) blocks Type-3 Summary LSAs in addition to Type-5 Externals. Only a default route (0.0.0.0/0 as Type-3) is injected by the ABR. If you need inter-area routes, use regular stub (allows Type-3) or normal area.

## Q41. OSPF with VRF-Lite.

**Answer:** Separate OSPF process per VRF. Process ID can be reused across VRFs (they're independent). Each VRF has its own LSDB, SPF calculation, and routing table.

```
router ospf 10 vrf CUSTOMER-A
  router-id 10.0.0.1
  network 10.10.0.0 0.0.255.255 area 0
router ospf 20 vrf CUSTOMER-B
  router-id 10.0.0.2
  network 10.20.0.0 0.0.255.255 area 0
```

## Q42. OSPF Segment Routing.

**Answer:** Replaces LDP for MPLS label distribution. Each router advertises a Prefix-SID (Segment ID) in its OSPF Router LSA. Other routers compute the SR-MPLS label stack using SPF. Benefits: no LDP sessions to maintain, traffic engineering via computed label stacks, source-based routing. Requires OSPF SR extensions (RFC 8665).

## Q43. Graceful OSPF maintenance procedure.

**Answer:** (1) Set `max-metric router-lsa` — router becomes least preferred transit. (2) Wait for traffic to drain (monitor interface counters — when transit traffic drops to near-zero, network has converged around this router). (3) Perform maintenance. (4) Remove `max-metric`. (5) Wait for SPF reconvergence. (6) Verify traffic returns to normal.

## Q44. Multi-vendor OSPF interoperability.

**Answer:** Stick to RFC-compliant features. Avoid vendor-specific extensions. Key differences: Cisco uses VRF-aware OSPF (process per VRF); Juniper uses routing instances. Timer defaults are the same across vendors (Hello 10s, Dead 40s) but verify. Authentication: MD5 is universal; SHA support varies. Network type defaults may differ — always configure explicitly.

## Q45. OSPF ECMP.

**Answer:** When multiple equal-cost paths exist to a destination, OSPF installs all of them. `maximum-paths` (default varies: Cisco IOS default 4, up to 32) controls how many. Traffic distribution is per-flow (hash-based), not per-packet. `show ip route <prefix>` shows multiple next-hops when ECMP is active.

## Q46. Transit area for virtual links cannot be stub.

**Answer:** Virtual links are carried as Type-1 Router LSAs with a special virtual-link indicator. Stub areas filter external LSAs and have restricted LSA types. The virtual link's control traffic would be filtered or mishandled in a stub area. Therefore, the transit area MUST be a normal (non-stub) area.

## Q47. Forward address in Type-5 LSAs.

**Answer:** When an ASBR redistributes an external route, the forward address in the Type-5 LSA can be set to the actual external destination (instead of the ASBR's address). This allows routers to route directly to the external destination if they have a more optimal path, bypassing the ASBR. Set when: the ASBR's interface to the external network is an OSPF-enabled interface, and the external next-hop is on an OSPF-enabled subnet.

## Q48. OSPF distribute-list behavior.

**Answer:** Critical misconception: `distribute-list` does NOT filter LSAs from the LSDB. The LSDB must stay synchronized across all routers in an area. `distribute-list in` filters routes from being installed in the routing table (RIB) on THIS router only. Other routers still have the route. This can cause asymmetric routing — use with extreme caution.

## Q49. ABR definition.

**Answer:** A router is an ABR if it has interfaces in at least two areas AND one of them is Area 0 (or it has a virtual link to Area 0). A router with interfaces in Area 1 and Area 2 but NOT Area 0 is NOT an ABR — it's a misconfiguration that breaks OSPF's hierarchy.

## Q50. Design: multi-site OSPF over MPLS.

**Answer:** Core MPLS network runs its own IGP (IS-IS or OSPF). Customer sites connect via PE-CE links running OSPF. Each site is an OSPF area (Area 1 for Site A, Area 2 for Site B). PE routers act as ABRs, summarizing each site's routes. MP-BGP VPNv4 carries routes across the MPLS core. Sham links if backdoor OSPF links exist between sites. NSSA for sites with local internet breakout (external routes via Type-7).


\newpage

# LINUX NETWORKING EXPANDED ANSWERS (Q6-Q50)

## Q6. Linux Bridge.

**Answer:** A software L2 switch in the kernel. Creates a bridge device, attach interfaces as ports. Supports STP, VLAN filtering, MAC learning. Docker's default bridge networking uses this — containers connect to `docker0` bridge via veth pairs.

```
ip link add br0 type bridge
ip link set eth0 master br0
ip link set br0 up
bridge link show                         # Show bridge ports
bridge vlan add dev eth0 vid 10          # VLAN filtering
brctl showstp br0                        # STP state (requires bridge-utils)
```

## Q7. Linux Routing and Policy Routing.

**Answer:** Standard routing: `ip route add 10.0.0.0/8 via 192.168.1.1`. Policy routing adds rules that select different routing tables based on source IP, mark, incoming interface, etc.

```
# Create a second routing table
echo "100 custom" >> /etc/iproute2/rt_tables

# Add rule: traffic from 10.0.1.0/24 uses table 100
ip rule add from 10.0.1.0/24 table 100

# Add default route in table 100 (different gateway)
ip route add default via 10.0.1.1 table 100
```

Use case: multi-homed server with two ISP connections. Traffic from ISP-A's IP uses ISP-A's gateway; traffic from ISP-B's IP uses ISP-B's gateway.

## Q8. TUN/TAP Devices.

**Answer:** **TUN:** Layer 3 device — operates on IP packets. Used by VPN software (OpenVPN in routing mode) to inject/receive IP packets into/from the kernel. **TAP:** Layer 2 device — operates on Ethernet frames. Used by VPN software in bridge mode, or by VMs (QEMU/KVM creates TAP devices for VM NICs). Both read/write from a file descriptor in userspace.

```
ip tuntap add dev tun0 mode tun user nobody
ip tuntap add dev tap0 mode tap user nobody
ip link set tun0 up
ip addr add 10.0.0.1/24 dev tun0
```

## Q9. VXLAN on Linux.

**Answer:** Linux kernel natively supports VXLAN. Each VXLAN interface acts as a VTEP.

```
# Create VXLAN interface with VNI 42, peer at 10.0.0.2
ip link add vxlan0 type vxlan id 42 remote 10.0.0.2 dstport 4789 dev eth0
ip link set vxlan0 up
ip addr add 192.168.100.1/24 dev vxlan0

# Verify
ip -d link show vxlan0                   # VXLAN details (VNI, port, remote)
bridge fdb show dev vxlan0               # FDB entries (MAC-to-VTEP mapping)
```

For multi-destination (multiple VTEPs), use `group 239.1.1.1` (multicast) instead of `remote` (unicast). In production, EVPN-based learning is preferred (Calico, FRRouting).

## Q10. XDP (eXpress Data Path).

**Answer:** eBPF programs attached at the earliest point in the NIC driver — before the kernel allocates a socket buffer (skb). This is the fastest possible packet processing in Linux. Actions: **XDP_PASS** (continue to normal stack), **XDP_DROP** (drop immediately — DDoS mitigation at 10+ Mpps per core), **XDP_TX** (bounce back out the same NIC — useful for load balancers), **XDP_REDIRECT** (send to another NIC or CPU). Use case: Cloudflare uses XDP to handle DDoS attacks at line rate without impacting application servers.

```
# Load XDP program
ip link set dev eth0 xdpgeneric obj xdp_drop.o sec xdp_prog
# Remove XDP program
ip link set dev eth0 xdpgeneric off
```

## Q11. tc (Traffic Control).

**Answer:** Linux's packet scheduling and shaping framework. Used for rate limiting, traffic shaping, classification, and policing. Cilium attaches eBPF programs at `tc ingress` and `tc egress` hooks for packet processing.

```
# Rate limit eth0 to 100 Mbps
tc qdisc add dev eth0 root tbf rate 100mbit burst 32kbit latency 400ms

# Show queuing disciplines
tc qdisc show dev eth0

# Add HTB (Hierarchical Token Bucket) for complex shaping
tc qdisc add dev eth0 root handle 1: htb default 10
tc class add dev eth0 parent 1: classid 1:10 htb rate 50mbit ceil 100mbit
```

## Q12. ip vs ifconfig.

**Answer:** `ip` (iproute2 package) is the modern standard. `ifconfig` (net-tools) is deprecated. Key replacements:

| Legacy | Modern |
|--------|--------|
| `ifconfig` | `ip addr show` |
| `ifconfig eth0 up` | `ip link set eth0 up` |
| `route` | `ip route show` |
| `route add` | `ip route add` |
| `arp -a` | `ip neigh show` |
| `netstat` | `ss` |
| `ifconfig eth0:0` (alias) | `ip addr add X dev eth0` (multiple IPs) |

`ip` supports features `ifconfig` can't handle: network namespaces, policy routing, VXLAN, bonding management, bridge VLAN filtering.

## Q13. ss vs netstat.

**Answer:** `ss` reads directly from the kernel via netlink — much faster than `netstat` (which reads `/proc`). On a server with 100K connections, `netstat` takes minutes; `ss` takes milliseconds.

```
ss -tlnp                     # TCP listening sockets with process name
ss -ulnp                     # UDP listening sockets
ss -s                        # Socket summary statistics
ss state established         # Only established connections
ss -tnp dst 10.0.0.0/8      # Filter by destination network
ss -i                        # Show TCP internal info (cwnd, rtt, retrans)
```

## Q14. tcpdump.

**Answer:** Packet capture tool. Uses libpcap to capture packets from the kernel.

```
tcpdump -i eth0 -nn port 80              # HTTP traffic, no DNS resolution
tcpdump -i any -nn host 10.0.0.1         # All traffic to/from specific host
tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-syn != 0'   # SYN packets only
tcpdump -i eth0 -nn -w capture.pcap      # Write to file (analyze in Wireshark)
tcpdump -r capture.pcap                   # Read from file
tcpdump -i eth0 -nn -c 100 port 179      # Capture 100 BGP packets
tcpdump -i vxlan.calico -nn              # Capture on Calico VXLAN interface
```

Critical flags: `-nn` (no name/port resolution — faster, clearer output), `-i any` (all interfaces), `-w` (write to pcap for Wireshark).

## Q15. nftables.

**Answer:** Replacement for iptables, ip6tables, arptables, ebtables — unified framework. Better syntax, atomic rule replacement (no flickering during updates), faster processing with set/map data structures. Kernel 3.13+.

```
nft list ruleset                          # Show all rules
nft add table inet filter                 # Create table (inet = IPv4 + IPv6)
nft add chain inet filter input { type filter hook input priority 0 \; }
nft add rule inet filter input tcp dport 22 accept
nft add rule inet filter input drop       # Default drop
```

Transition: `iptables-nft` provides iptables syntax compatibility on top of nftables backend.

## Q16. Network Bonding.

**Answer:** Combines multiple NICs into one logical interface for redundancy and/or bandwidth.

```
ip link add bond0 type bond mode 802.3ad    # LACP
ip link set eth0 master bond0
ip link set eth1 master bond0
ip link set bond0 up
```

**Modes:** 0 (round-robin — load balance, not recommended for TCP), 1 (active-backup — redundancy), 2 (balance-xor — hash-based), 3 (broadcast — all interfaces), 4 (802.3ad/LACP — requires switch support, best for production), 5 (balance-tlb — outgoing LB, no switch config), 6 (balance-alb — both directions, no switch config).

## Q17. MTU and Path MTU Discovery.

**Answer:** Default MTU: 1500 bytes. Jumbo frames: up to 9000 bytes (must be enabled on every device in the path). PMTUD uses ICMP "Fragmentation Needed" (Type 3, Code 4) to discover the lowest MTU on a path. If a firewall blocks ICMP, PMTUD fails — TCP connections establish but hang when transferring data larger than the bottleneck MTU (PMTUD black hole).

Fix: clamp TCP MSS to match PMTU:

```
iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu
```

Testing: `ping -s 1472 -M do <destination>` — sends 1500-byte packet (1472 payload + 20 IP + 8 ICMP). If it fails, MTU is less than 1500 somewhere.

## Q18. ARP.

**Answer:** Resolves IPv4 addresses to MAC addresses on the local segment. ARP request (broadcast): "Who has 10.0.0.1?" ARP reply (unicast): "10.0.0.1 is at 00:11:22:33:44:55." Cache: entries timeout after ~30-300 seconds (OS-dependent).

```
ip neigh show                             # ARP table
ip neigh add 10.0.0.2 lladdr 00:11:22:33:44:55 dev eth0   # Static entry
ip neigh flush dev eth0                   # Clear ARP cache
arping -I eth0 10.0.0.1                  # Send ARP request manually
```

**Gratuitous ARP:** An ARP announcement (request for own IP) — used by HSRP/VRRP to update switches' MAC tables during failover.

## Q19. /proc/sys/net Tuning Parameters.

**Answer:** Critical parameters for network performance and security:

```
# Routing
net.ipv4.ip_forward = 1                   # Enable IPv4 routing (required for routers/containers)

# TCP Performance
net.core.somaxconn = 4096                 # TCP listen backlog
net.core.rmem_max = 16777216              # Max socket receive buffer (16MB)
net.core.wmem_max = 16777216              # Max socket send buffer
net.ipv4.tcp_rmem = 4096 87380 16777216  # TCP receive buffer (min, default, max)
net.ipv4.tcp_wmem = 4096 65536 16777216  # TCP send buffer
net.ipv4.tcp_tw_reuse = 1                # Reuse TIME_WAIT sockets (for outbound)
net.ipv4.tcp_fin_timeout = 30            # FIN_WAIT2 timeout

# Conntrack (critical for K8s/containers)
net.netfilter.nf_conntrack_max = 1048576 # Max tracked connections
net.netfilter.nf_conntrack_tcp_timeout_established = 86400

# Security
net.ipv4.conf.all.rp_filter = 1          # Reverse path filtering (anti-spoofing)
net.ipv4.icmp_echo_ignore_broadcasts = 1 # Ignore broadcast pings (smurf attack)
net.ipv4.conf.all.accept_redirects = 0   # Ignore ICMP redirects
net.ipv4.conf.all.send_redirects = 0
```

## Q20. systemd-networkd vs NetworkManager.

**Answer:** **systemd-networkd:** Lightweight, headless, config-file-driven (`/etc/systemd/network/*.network`). Ideal for servers and containers. Integrates with systemd-resolved for DNS. **NetworkManager:** Feature-rich, GUI-aware, supports Wi-Fi, VPN, mobile broadband. Ideal for desktops/laptops with dynamic networking. **netplan (Ubuntu):** YAML abstraction that generates config for either systemd-networkd or NetworkManager as backend. In production servers: use systemd-networkd or direct netplan configuration.

## Q21. DNS Resolution on Linux.

**Answer:** Resolution chain: (1) Application calls `getaddrinfo()`. (2) glibc reads `/etc/nsswitch.conf` for resolution order (`files dns` = check /etc/hosts first, then DNS). (3) DNS queries sent to nameservers in `/etc/resolv.conf`. (4) On modern systems, `systemd-resolved` intercepts — provides caching, per-interface DNS, DNSSEC validation. Stub resolver at 127.0.0.53.

```
resolvectl status                         # Per-interface DNS config
resolvectl query example.com              # Resolve with details
cat /etc/resolv.conf                      # Effective nameserver config
dig example.com @8.8.8.8 +trace          # Full DNS trace
```

## Q22. Firewalld.

**Answer:** Dynamic firewall manager with zones (public, internal, dmz, trusted, etc.) and services abstraction. Generates iptables or nftables rules underneath.

```
firewall-cmd --get-active-zones
firewall-cmd --zone=public --list-all
firewall-cmd --zone=public --add-service=https --permanent
firewall-cmd --zone=public --add-port=8080/tcp --permanent
firewall-cmd --reload
```

For container/router scenarios, raw iptables/nftables is preferred for precise control.

## Q23. Network Performance Tuning.

**Answer:** (1) **Ring buffers:** `ethtool -G eth0 rx 4096 tx 4096` — increase NIC ring buffer to reduce packet drops under load. (2) **RSS/RPS:** Receive Side Scaling distributes incoming packets across multiple CPU cores. `ethtool -L eth0 combined 8` — 8 queues. (3) **Interrupt coalescing:** `ethtool -C eth0 rx-usecs 100` — batch interrupts to reduce CPU overhead (trade-off: slight latency increase). (4) **TCP BBR:** `sysctl net.ipv4.tcp_congestion_control=bbr` — Google's congestion control algorithm, better throughput on lossy networks. (5) **GRO/GSO/TSO:** `ethtool -K eth0 gro on gso on tso on` — offload segmentation to NIC hardware.

## Q24. WireGuard.

**Answer:** Modern VPN protocol built into the Linux kernel since 5.6. Simpler than IPsec/OpenVPN. Uses Curve25519 (key exchange), ChaCha20-Poly1305 (encryption), BLAKE2s (hashing). ~4000 lines of code (vs OpenVPN's 100K+).

```
# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey

# Configure interface
ip link add wg0 type wireguard
wg set wg0 private-key ./privatekey listen-port 51820 \
  peer <PEER_PUBKEY> endpoint <PEER_IP>:51820 allowed-ips 10.0.0.0/24
ip addr add 10.0.0.1/24 dev wg0
ip link set wg0 up

# Status
wg show
```

## Q25. Network Troubleshooting Workflow.

**Answer:** Systematic bottom-up approach:

```
# 1. Interface status
ip addr show                              # IPs, interface state
ip link show                              # Link state (UP/DOWN)
ethtool eth0                              # Speed, duplex, link detected

# 2. Routing
ip route show                             # Routing table
ip route get 10.0.0.1                     # Which route for destination?

# 3. Name resolution
cat /etc/resolv.conf                      # DNS config
dig example.com                           # DNS resolution test

# 4. Connectivity
ping -c 3 <gateway>                       # Gateway reachable?
traceroute -n <destination>               # Where does path break?
mtr -n <destination>                      # Real-time traceroute with stats

# 5. Port/service
ss -tlnp                                  # What's listening?
curl -v http://10.0.0.1:80               # Application-level test

# 6. Firewall
iptables -L -n -v                         # Filter rules
iptables -t nat -L -n -v                  # NAT rules
conntrack -L                              # Connection tracking

# 7. Packet analysis
tcpdump -i eth0 -nn host 10.0.0.1        # Capture specific traffic
```

## Q26-Q50 (Remaining Linux topics — key answers):

**Q26. ip rule and policy routing:** Multiple routing tables selected by source IP, mark, or incoming interface. `ip rule show` lists rules in priority order. Lower priority number = evaluated first.

**Q27. ebtables:** L2 filtering on Linux bridges. Filter by MAC address, VLAN tag, ARP opcode. Being replaced by nftables bridge family.

**Q28. macvlan/ipvlan:** macvlan assigns multiple MAC addresses to a physical NIC — each macvlan interface has its own MAC and can be in a separate namespace. ipvlan shares the parent's MAC but assigns different IPs. macvlan can't communicate with the parent interface (by design). Used for container networking as an alternative to bridges.

**Q29. Persistent network namespaces:** `ip netns add` creates named namespaces in `/var/run/netns/`. Persist across reboots with systemd unit files. Container runtimes use unnamed namespaces (linked via `/proc/<pid>/ns/net`).

**Q30. /sys/class/net:** Exposes NIC information as files. `cat /sys/class/net/eth0/speed` (link speed), `operstate` (up/down), `address` (MAC), `statistics/rx_bytes`. Useful for monitoring scripts.

**Q31. ethtool diagnostics:** `ethtool eth0` (speed, duplex, link), `ethtool -S eth0` (NIC statistics — rx_errors, tx_drops, collisions), `ethtool -i eth0` (driver info), `ethtool -k eth0` (offload features).

**Q32. iperf3:** Network bandwidth testing. Server: `iperf3 -s`. Client: `iperf3 -c <server> -t 30 -P 4` (30 seconds, 4 parallel streams). Reports bandwidth, jitter, packet loss. Essential for validating link capacity.

**Q33. mtr:** Combines traceroute and ping. `mtr -n <destination>` shows per-hop loss and latency in real-time. Better than `traceroute` for identifying intermittent issues — accumulates statistics over time.

**Q34. TCP stack internals:** SYN arrives → enters SYN queue (backlog `tcp_max_syn_backlog`). After 3-way handshake → moves to accept queue (`somaxconn`). `listen()` call defines backlog size. SYN flood: SYN queue fills up, legitimate connections dropped. Mitigation: SYN cookies (`net.ipv4.tcp_syncookies = 1`).

**Q35. TCP BBR vs Cubic:** Cubic (default) is loss-based — reduces window on packet loss. BBR is model-based — estimates bottleneck bandwidth and RTT, maintains optimal sending rate regardless of random loss. BBR significantly improves throughput on lossy networks (WAN, mobile).

**Q36. SO_REUSEPORT:** Socket option allowing multiple processes to bind to the same port. Kernel distributes incoming connections across all listening sockets (round-robin or hash-based). Used by NGINX, Envoy for multi-process load balancing.

**Q37. eBPF (reinforced):** Write programs in C → compile to eBPF bytecode → verifier checks safety → JIT to native code → attach to kernel hooks. Maps (hash, array, LRU, ring buffer) for data exchange between kernel and userspace. Tools: `bpftool prog list`, `bpftool map dump`.

**Q38. systemd socket activation:** systemd listens on a socket. When a connection arrives, systemd starts the service and passes the socket fd. Service starts on-demand. Reduces boot time and resource usage for rarely-used services.

**Q39. sysctl hardening:** Disable IP source routing (`accept_source_route = 0`), enable SYN cookies, disable ICMP redirects, enable reverse path filtering, log martian packets (`log_martians = 1`).

**Q40. VLAN tagging on Linux (8021q):** `modprobe 8021q`, `ip link add link eth0 name eth0.10 type vlan id 10`, `ip addr add 10.0.10.1/24 dev eth0.10`, `ip link set eth0.10 up`. Creates a sub-interface tagged with VLAN 10.

**Q41. GRE tunnels on Linux:** `ip tunnel add gre1 mode gre remote 203.0.113.2 local 198.51.100.1 ttl 255`, `ip addr add 10.0.0.1/30 dev gre1`, `ip link set gre1 up`. MTU = parent MTU - 24 (GRE overhead).

**Q42. IPv6 on Linux:** SLAAC auto-configures IPv6 from Router Advertisements. `ip -6 addr show`, `ip -6 route show`. Privacy extensions (`use_tempaddr = 2`) generate temporary addresses for outbound connections. DHCPv6 for managed address assignment.

**Q43. DPDK:** Bypasses the kernel network stack entirely. NIC is bound to a userspace driver (UIO/VFIO). Application processes packets directly in userspace with zero kernel overhead. Used in NFV (virtual routers, firewalls) for 10-100 Gbps line-rate processing.

**Q44. AF_PACKET:** Raw socket access to L2 frames. `socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL))`. Used by tcpdump, Wireshark, and network monitoring tools. Can read and inject raw Ethernet frames.

**Q45. PXE boot:** Network boot sequence: DHCP → TFTP (download boot image) → boot. DHCP option 66 (next-server) and option 67 (bootfile-name). Used for ZTP of network devices and OS deployment at scale.

**Q46. Linux as a router:** Enable `ip_forward=1`. Run FRRouting (formerly Quagga) for OSPF, BGP, IS-IS, MPLS. `vtysh` provides Cisco-like CLI. Used in production by large cloud providers (Google runs BGP on Linux routers).

**Q47. Netfilter hooks:** PREROUTING, INPUT, FORWARD, OUTPUT, POSTROUTING. Custom kernel modules can register at these hooks with a priority value. iptables, nftables, conntrack, and eBPF all use Netfilter hooks.

**Q48. cgroup network bandwidth limiting:** cgroup v2 + eBPF programs can rate-limit network traffic per container/process. Kubernetes uses this for Pod bandwidth annotations. `tc` with cgroup classifiers provides shaping per cgroup.

**Q49. DNS troubleshooting:** `dig +trace example.com` — traces resolution from root servers down. `dig @8.8.8.8 example.com` — query specific server. `strace -e trace=network curl http://example.com` — see DNS system calls. Check `/etc/nsswitch.conf` for resolution order. `resolvectl flush-caches` — clear systemd-resolved cache.

**Q50. Advanced: Monitoring with /proc and /sys:** `/proc/net/dev` — per-interface byte/packet/error counters. `/proc/net/tcp` — all TCP connections (socket inode, state, queues). `/proc/net/sockstat` — socket usage summary. `/sys/class/net/<iface>/statistics/` — NIC-level stats. Poll these for custom monitoring when SNMP is unavailable.


\newpage

# SWITCHING EXPANDED ANSWERS (Q11-Q50)

## Q11. MSTP (802.1s).

**Answer:** Multiple Spanning Tree Protocol maps multiple VLANs to fewer STP instances. PVST+ runs one STP instance per VLAN — 100 VLANs = 100 STP instances = significant CPU overhead. MSTP groups VLANs into instances: Instance 1 handles VLANs 1-50, Instance 2 handles VLANs 51-100. Each instance has its own Root Bridge and topology. Reduces STP overhead while maintaining per-group traffic engineering. Configuration: `spanning-tree mode mst`, define MST region (name, revision, VLAN-to-instance mapping) — must match on all switches in the region.

## Q12. LACP fast timers.

**Answer:** Default LACP rate: slow (30-second PDU interval). Fast: 1-second interval. Detect link failure in 3 seconds (3 missed PDUs) instead of 90 seconds. Essential for fast failover. Configure: `lacp rate fast` on the interface. Both sides must match. Use fast timers on critical uplinks.

## Q13. EtherChannel misconfiguration scenarios.

**Answer:** (1) One side On, other side LACP Active → No channel (On disables negotiation). (2) Both sides LACP Passive → No channel (neither initiates). (3) Speed/duplex mismatch between member ports → ports suspended. (4) VLAN mismatch (one port access VLAN 10, another access VLAN 20) → channel won't form. (5) Different STP port costs on members → channel won't form. All member ports must have identical configuration (speed, duplex, VLAN, STP).

## Q14. Storm Control.

**Answer:** Rate-limits broadcast, multicast, or unknown unicast traffic per port. Prevents broadcast storms from consuming all bandwidth. Actions: shutdown, trap (SNMP alert), or errdisable.

```
interface GigabitEthernet0/1
  storm-control broadcast level 10        ! Limit broadcast to 10% of bandwidth
  storm-control multicast level 10
  storm-control action shutdown           ! Shutdown port on violation
```

## Q15. Port Security.

**Answer:** Limits the number of MAC addresses allowed on a port. Violation modes: **Shutdown** (err-disables the port — default, most secure), **Restrict** (drops frames from unknown MACs, logs, increments violation counter), **Protect** (drops silently, no log).

```
interface GigabitEthernet0/1
  switchport mode access
  switchport port-security
  switchport port-security maximum 2
  switchport port-security violation shutdown
  switchport port-security mac-address sticky    ! Learn and save MACs
```

## Q16. SPAN/RSPAN/ERSPAN.

**Answer:** **SPAN (Switched Port Analyzer):** Mirrors traffic from source port(s)/VLAN to a local destination port (where a packet capture device/IDS is connected). Source and destination must be on the same switch. **RSPAN:** Extends SPAN across switches using a dedicated RSPAN VLAN. Mirrored traffic is tagged with the RSPAN VLAN and transported over trunks to a remote switch's destination port. **ERSPAN:** Extends SPAN over L3 using GRE encapsulation. Mirrored traffic is GRE-encapsulated and routed to a remote destination IP anywhere in the network. Most flexible but adds GRE overhead.

```
! Local SPAN
monitor session 1 source interface Gi0/1
monitor session 1 destination interface Gi0/24
```

## Q17. UDLD (Unidirectional Link Detection).

**Answer:** Detects unidirectional links — where one fiber strand is working but the other is broken. Without UDLD, STP sees the port as up (the working receive strand shows link), but the switch can't send. This can cause loops or black holes. UDLD sends probes; if the neighbor doesn't echo back, the port is err-disabled. Modes: **Normal** (alerts), **Aggressive** (err-disables the port). Enable on all fiber uplinks.

```
udld aggressive
interface GigabitEthernet0/1
  udld port aggressive
```

## Q18. StackWise/VSS.

**Answer:** **StackWise (Catalyst 9000):** Multiple physical switches connected via stack cables act as a single logical switch. One master, others members. Single management IP, unified config, unified spanning-tree. Stack ring provides redundancy — if one link breaks, traffic reverses direction. **VSS (Virtual Switching System, 6500/4500):** Two chassis form one logical switch with MEC (Multi-chassis EtherChannel). Control plane active on one chassis, forwarding on both. Being replaced by StackWise Virtual in Catalyst 9000 series.

## Q19. Loop Guard.

**Answer:** Prevents a designated or root port from becoming forwarding due to loss of BPDUs. If BPDUs stop arriving on a root/designated port (upstream switch failure, unidirectional link), without Loop Guard the port would transition to designated-forwarding (since it thinks it's the only switch on the segment), potentially creating a loop. Loop Guard puts the port into loop-inconsistent blocking state instead. Complements UDLD — UDLD detects unidirectional links, Loop Guard prevents loops from BPDU loss.

## Q20. VLAN Access Maps (VACM).

**Answer:** L2 ACLs applied to traffic within a VLAN (intra-VLAN filtering). Standard ACLs are applied at L3 (routed interfaces). VACMs can filter, redirect, or drop traffic based on MAC address, IP, or protocol without routing. Use case: prevent two hosts in the same VLAN from communicating.

```
vlan access-map FILTER 10
  match ip address ACL-DENY-SSH
  action drop
vlan access-map FILTER 20
  action forward
vlan filter FILTER vlan-list 10
```

## Q21-Q30: Switching Troubleshooting Scenarios.

**Q21. MAC flapping:** Same MAC seen on two different ports alternating rapidly. Causes: loop (STP misconfiguration), VM migration, duplicate MAC (very rare). `show mac address-table notifications` and log messages identify the MAC and ports. Fix: trace the loop or identify the VM migration path.

**Q22. STP loop:** Broadcast storm, high CPU on all switches, MAC flapping across multiple ports. Root cause: BPDU Guard not enabled, rogue switch connected, or fiber unidirectional fault. Immediate fix: shut the suspected port. Long-term: enable BPDU Guard on all access ports, Root Guard on distribution downlinks, UDLD on fiber.

**Q23. Trunk negotiation failure:** `show interface trunk` shows no trunk. Common causes: one side `switchport mode access`, DTP not agreeing (one side `dynamic desirable`, other `dynamic auto` works; both `auto` doesn't). Fix: hard-code `switchport mode trunk` on both sides, `switchport nonegotiate`.

**Q24. VLAN mismatch on trunk:** VLAN 10 allowed on one side but not the other. Traffic for VLAN 10 is carried on the trunk from Switch A but dropped on Switch B. `show interface trunk` on both sides — compare allowed VLANs. Fix: ensure `switchport trunk allowed vlan` lists match.

**Q25. Native VLAN mismatch:** Switch A native VLAN 1, Switch B native VLAN 99. CDP/STP detects mismatch and logs a warning. Untagged frames from A (VLAN 1) are placed into VLAN 99 on B. Potential security issue and traffic leakage. Fix: match native VLANs on both sides.

**Q26. EtherChannel load balancing uneven:** One link carries 80% of traffic. Cause: the hash algorithm selects the same link for dominant flows. Fix: change hash method (`port-channel load-balance src-dst-ip` or add port to the hash: `src-dst-ip-port`). Monitor per-member traffic: `show etherchannel <number> port-channel`.

**Q27. err-disabled recovery:** Port shut by BPDU Guard, port security, or UDLD. Manual recovery: `shut` then `no shut`. Auto recovery: `errdisable recovery cause bpduguard`, `errdisable recovery interval 300` (try every 300 seconds).

**Q28. Root bridge instability:** A new switch with lower MAC becomes Root, reshaping topology. All traffic reroutes through an access switch. Fix: explicit priority configuration on designated root switches.

**Q29. UDLD detection on fiber:** Single fiber strand failure detected by UDLD. Port err-disabled. Replace fiber, clear err-disable. Without UDLD, this would be a silent black hole.

**Q30. Broadcast storm without STP loop:** Possible causes: malware (broadcast flood from infected host), ARP storm (many hosts ARP-requesting simultaneously), faulty NIC sending continuous broadcasts. Fix: storm control rate-limits broadcasts per port.

## Q31-Q40: Switching Design.

**Q31. Campus design:** Three-tier (access → distribution → core) or two-tier (access → collapsed core/distribution). L3 at distribution eliminates STP between tiers. Access switches: portfast, BPDU guard, 802.1X. Distribution: inter-VLAN routing via SVIs, route summarization to core.

**Q32. Inter-VLAN routing options:** (1) Router-on-a-stick: single router interface with 802.1Q sub-interfaces. Simple but bottleneck. (2) L3 switch SVIs: wire-rate routing in hardware. Preferred for campus and DC. (3) Dedicated router per VLAN: overkill, only for extreme policy requirements.

**Q33. VLAN sprawl management:** Define VLAN naming standards. Limit VLAN scope to a single switch or closet (avoid stretching VLANs across the campus). Use routed access where possible. Document VLAN assignments in a source of truth (NetBox/Nautobot).

**Q34. QoS at the access layer:** Classify and mark traffic at ingress. Voice traffic marked DSCP EF (46). Signaling marked CS3 (24). Video marked AF41 (34). Data marked AF21 (18) or default. Trust DSCP from known devices (IP phones), remark from untrusted (PCs). Apply queuing policy on uplinks.

**Q35. Voice VLAN:** Cisco phones support auxiliary VLAN. `switchport voice vlan 20` — phone tags voice traffic with VLAN 20, passes PC traffic untagged on data VLAN. CDP/LLDP-MED tells the phone which VLAN to use.

**Q36. L3 routed access:** Every switch uplink is a routed interface (no L2 trunks, no VLANs spanning switches, no STP). Each switch is its own L2 domain. Inter-switch communication is L3 routed. Modern best practice for new campus deployments. Eliminates STP complexity entirely.

**Q37. Multi-site VLAN extension:** Generally avoid. Stretching L2 across WAN creates a massive failure domain. If unavoidable, use OTV or VXLAN with strict storm control and BUM traffic limiting. Better alternative: route between sites, use application-level solutions for mobility.

**Q38. VLAN naming conventions:** Descriptive and consistent. Format: `VLAN_<site>_<function>_<number>`. Example: VLAN_NYC_DATA_10, VLAN_NYC_VOICE_20, VLAN_NYC_MGMT_99. Document in the source of truth.

**Q39. Management VLAN:** Separate VLAN for switch/AP management traffic. Not VLAN 1 (default, commonly targeted). ACL restrict management VLAN access to network admin IPs only. SSH only (no telnet).

**Q40. Wireless VLAN design:** Separate VLANs for corporate SSID (802.1X), guest SSID (captive portal), IoT devices. Guest VLAN routes directly to internet via firewall — no access to corporate VLANs.

## Q41-Q50: Advanced Switching.

**Q41. MACsec (802.1AE):** Hop-by-hop L2 encryption. Encrypts entire Ethernet frame between adjacent switches. Provides confidentiality, integrity, and authenticity at L2. Uses AES-GCM-256. Key exchange via MKA (MACsec Key Agreement, 802.1X-2010). Use on sensitive trunk links.

**Q42. 802.1X with RADIUS:** Port-based authentication. Supplicant (PC) → Authenticator (switch port) → Authentication Server (RADIUS/ISE/ClearPass). EAP exchange. RADIUS returns VLAN assignment, ACL, or SGT (Security Group Tag). Failed auth → guest VLAN or port shutdown.

**Q43. Dynamic VLAN assignment:** RADIUS attribute Tunnel-Type (13), Tunnel-Medium-Type (6), Tunnel-Private-Group-ID (VLAN number). Based on user identity (AD group), device type (MAC OUI), or posture assessment (compliant = VLAN 10, non-compliant = remediation VLAN 99).

**Q44. Cisco TrustSec/SGT:** Security Group Tags assigned at ingress based on identity. Tags travel with the frame (inline tagging or SXP propagation). SGACLs enforce policy based on source SGT → destination SGT, regardless of IP. Simplifies policy management in large networks — policy follows the user, not the IP.

**Q45. Fabric technologies replacing STP:** Cisco SD-Access (LISP + VXLAN + TrustSec), Aruba Fabric Composer, Juniper EVPN-VXLAN campus fabric. All use L3 underlay with overlay tunnels, eliminating STP entirely. Provide macro-segmentation (VRF per group), micro-segmentation (SGT/ACL), and simplified management.

**Q46. PVST+ vs RPVST+:** PVST+ = Per-VLAN STP (802.1D per VLAN, slow convergence). RPVST+ = Rapid PVST+ (802.1w per VLAN, sub-second convergence). Always use RPVST+ or MST. Legacy PVST+ should never be deployed.

**Q47. STP Topology Change mechanism:** When a link goes down/up, the detecting switch sends a TCN (Topology Change Notification) BPDU toward the Root Bridge. Root Bridge sets the TC flag in its configuration BPDUs for `forward_delay` seconds. All switches receiving TC-flagged BPDUs shorten their MAC table aging time from 300s to 15s, causing faster MAC relearning. This is necessary but causes brief flooding as MAC tables are cleared.

**Q48. STP pathcost method:** Short (legacy, 16-bit): max cost 65535. 10G and 100G links both get cost 2 — indistinguishable. Long (32-bit): max cost 200000000. 10G = 2000, 100G = 200. Use long method: `spanning-tree pathcost method long`.

**Q49. STP dispute mechanism:** If a designated port receives an inferior BPDU (lower priority than its own) from a port that claims to be designated, STP dispute puts the receiving port into blocking. Prevents loops from unidirectional links where the remote switch doesn't see the local switch's BPDUs.

**Q50. Troubleshooting exercise: reading `show spanning-tree` output.** Key things to check: (1) Is the expected switch the Root? Check Bridge ID vs Root ID. (2) Are the expected ports Root/Designated/Alternate? Check port roles. (3) Are costs consistent? (4) Are there any ports in BLK state that shouldn't be? (5) Is the topology stable? Check `Number of topology changes` and `Time since last topology change`.


\newpage

# DC TECHNOLOGIES EXPANDED ANSWERS (Q4-Q50)

## Q4. EVPN-VXLAN control plane.

**Answer:** EVPN uses MP-BGP (address family L2VPN EVPN) to distribute MAC/IP information between VTEPs. Route Type 2 (MAC/IP Advertisement): "MAC 00:11:22:33:44:55 with IP 10.0.1.5 is behind VTEP 10.255.0.1 in VNI 10010." Route Type 3 (Inclusive Multicast Ethernet Tag): establishes BUM (Broadcast, Unknown unicast, Multicast) replication lists. Route Type 5 (IP Prefix): carries L3 routes for inter-VNI routing (symmetric IRB). This eliminates flood-and-learn — VTEPs know MAC locations before the first data packet, reducing unknown unicast flooding to zero.

## Q5. vPC (Virtual PortChannel) deep dive.

**Answer:** (Covered in main guide Q14.) Additional operational details: **Type-1 consistency check (hard):** Parameters that MUST match between peers or vPC suspends — STP mode, VLAN existence, STP port type (edge/normal). **Type-2 consistency check (soft):** Parameters that SHOULD match — STP cost, interface speed. Mismatch generates warning but doesn't suspend. **CFS (Cisco Fabric Services):** Protocol running over peer-link for synchronizing MAC tables, ARP tables, IGMP snooping state. **Peer-gateway:** Allows each vPC peer to act as the gateway for the other's packets — handles traffic arriving with the wrong peer's router MAC. Enable: `peer-gateway`.

## Q6. FEX (Fabric Extender).

**Answer:** Nexus 2000 series. Acts as a remote line card for a parent Nexus 5000/7000/9000. No local control plane — all configuration, forwarding decisions, and management happen on the parent. Connected via FEX fabric (typically 10G uplinks). Benefits: simplified management (one device to manage), reduced OPEX, consistent policy. Drawback: dependent on parent — if parent fails, all FEX ports go down. Deployment: ToR in server racks, parent in EoR or MoR position.

## Q7. Bare-metal vs overlay networking.

**Answer:** **Bare-metal (underlay):** Physical switches, routed L3 fabric (eBGP/OSPF), VLANs for server-facing L2 segments. Simple, low overhead. Limited to 4094 VLANs. Workload mobility constrained by VLAN scope. **Overlay:** VXLAN/NVGRE/Geneve tunnels over the L3 underlay. 16M+ segments. Workload mobility — VMs/containers move anywhere without IP changes. Adds encapsulation overhead (50 bytes for VXLAN). Modern DCs use overlay for multi-tenancy and mobility, underlay for physical connectivity and routing.

## Q8. DC Interconnect (DCI).

**Answer:** Connecting two or more data centers at L2 or L3. Options: (1) **VXLAN multi-site:** Extend VXLAN fabric across sites. BGW (Border Gateway) nodes handle inter-site EVPN route exchange. Each site has its own underlay. (2) **OTV (Overlay Transport Virtualization):** Cisco proprietary, extends L2 over L3. Built-in loop prevention (OTV doesn't forward STP BPDUs). (3) **Dark fiber / DWDM:** Direct L1 connectivity for low latency. (4) **EVPN multi-homing:** Active-active connectivity to dual-homed DCI links. Best practice: minimize L2 stretch between sites. Prefer L3 DCI with application-level failover.

## Q9. East-west vs north-south traffic.

**Answer:** **North-south:** Traffic entering/leaving the DC (client → server). Passes through the DC border/firewall. Traditionally the dominant pattern. **East-west:** Traffic between servers within the DC (app server → database, microservice → microservice). In modern architectures (microservices, containers), east-west dominates (80%+ of DC traffic). Spine-leaf is optimized for east-west — equal-cost paths between any two leaves. Security: east-west traffic needs micro-segmentation (ACI contracts, NSX DFW, Cilium NetworkPolicy) since it doesn't traverse the perimeter firewall.

## Q10. Micro-segmentation.

**Answer:** Security within the DC — controlling traffic between workloads in the same segment. Traditional firewalls only see north-south. Micro-segmentation enforces policy east-west. Implementations: ACI Contracts (EPG-to-EPG rules), NSX-T Distributed Firewall (per-VM rules enforced at the hypervisor vSwitch), Cilium NetworkPolicy (per-Pod rules in Kubernetes), Cisco TrustSec SGACLs. Zero-trust principle: even workloads in the same subnet must be explicitly allowed to communicate.

## Q11-Q50 (Condensed but substantive):

**Q11.** Server NIC bonding to dual ToR: LACP to vPC/MLAG pair. Active-active uplinks. If one ToR fails, traffic continues via the surviving ToR without reconvergence. **Q12.** Lossless Ethernet for storage/RDMA: PFC (Priority Flow Control, 802.1Qbb) pauses specific CoS classes. ECN (Explicit Congestion Notification) marks packets instead of dropping. Required for RoCE (RDMA over Converged Ethernet). **Q13.** iSCSI vs FC vs NFS: iSCSI = block storage over TCP/IP (easy, runs on Ethernet). FC = dedicated Fibre Channel network (highest performance, separate infrastructure). NFS = file storage over TCP/IP. FCoE = FC frames over lossless Ethernet (converges storage and data on one network).

**Q14-Q20.** DC power redundancy (A+B feeds). ToR vs MoR vs EoR switch placement trade-offs. Oversubscription ratios (3:1 for general compute, 1:1 for HPC/AI). Spine capacity planning formula. SDN controllers (APIC, NSX Manager, OpenDaylight). NSX-T Transport Zones and N-VDS. SmartNIC/DPU offload (NVIDIA BlueField runs OVS/VXLAN/IPsec on the NIC, freeing host CPU).

**Q21-Q28.** SONiC architecture (SAI abstraction, FRRouting for control plane, Redis for state DB). Cumulus Linux (now NVIDIA, switchd for ASIC programming). DC automation with Ansible (cisco.nxos collection), Terraform for cloud integration. Day-0 (provision), Day-1 (configure), Day-2 (operate/monitor). ZTP (DHCP option 67 → bootstrap script). GitOps (config in Git → CI pipeline validates → deploys to switches). EVPN Type-5 for L3 inter-VNI routing (advertises IP prefixes, not MAC/IP bindings). Asymmetric IRB (route on ingress leaf, bridge on egress leaf — simpler but requires all VNIs on all leaves) vs Symmetric IRB (route on both, uses L3 VNI — scales better, VNIs only where needed).

**Q29-Q40.** Multi-tenancy with VRFs mapped to VNIs. ACI vs NX-OS standalone comparison (ACI = policy-driven SDN, NX-OS = traditional CLI config). Troubleshooting VXLAN tunnel failures (verify VTEP reachability, NVE peer state, VNI mapping). ACI contract debugging (check EPG-to-Contract binding, contract filters, Tenant config). vPC peer-link issues (keepalive timeout → secondary suspends). VTEP reachability via underlay routing (show nve peers). Overlay vs underlay diagnosis (is the problem in the VXLAN tunnel or the physical path?). MTU with VXLAN (need 1550+ on underlay to accommodate 50-byte overhead). TCAM exhaustion on leafs (reduce route count with summarization, check hardware profile). BUM storm containment (ARP suppression in EVPN, ingress replication lists, storm control on access ports).

**Q41-Q50.** Design exercises: 1000-server fabric (4 spines, 40 leaves, 48-port, 3:1 oversubscription). Multi-site active-active (VXLAN multi-site with BGW, anycast gateway for seamless VM mobility). DR site connectivity (L3 DCI preferred, dark fiber or MPLS). Legacy three-tier to spine-leaf migration (phased approach, VLANs on new leaves, migrate servers rack by rack). 400G spine planning (Nexus 9364D-GX2A or Arista 7060X5, consider future bandwidth growth). Multi-tenant DC design (VRFs per tenant, separate VNI ranges, per-tenant firewalling). Firewall placement in spine-leaf (service chain via PBR to firewall VMs, or east-west via ACI contracts/NSX DFW). Monitoring strategy (Telegraf + InfluxDB + Grafana for NX-OS streaming telemetry, Syslog aggregation, SNMP for legacy). Capacity planning methodology (measure current utilization, project growth, plan fabric expansion). Brownfield vs greenfield DC design considerations.

\newpage

# CLOUD NETWORKING EXPANDED ANSWERS (Q4-Q50)

## Q4-Q10 (Azure connectivity and services):

**Q4.** Azure VPN Gateway supports IKEv2 and OpenVPN (P2S). SKUs: VpnGw1 (650 Mbps) through VpnGw5 (10 Gbps). Active-active with two public IPs and two tunnels for redundancy. BGP over VPN supported — exchange routes dynamically with on-prem.

**Q5.** ExpressRoute: private peering (access VNets), Microsoft peering (access Microsoft 365, Azure PaaS public IPs). Two circuits for redundancy at different peering locations. ExpressRoute Global Reach connects two on-prem sites through Microsoft backbone. FastPath bypasses the gateway for direct connection to VNet.

**Q6.** Virtual WAN: managed hub-spoke. Azure-managed VNet hub with auto-provisioned VPN/ExpressRoute gateways. SD-WAN integration (Barracuda, Cisco Viptela, Palo Alto Prisma). Inter-hub routing automatic. Secured Virtual Hub = hub with Azure Firewall integrated.

**Q7.** Azure DNS: public zones (internet-facing) and private zones (VNet-internal). Private DNS Resolver enables on-prem → Azure private zone resolution and vice versa. CNAME flattening for apex domains not supported (use alias records instead).

**Q8.** Azure Load Balancer: L4 (TCP/UDP). Standard SKU required for production. HA ports rule — load-balance ALL protocols and ports to backend pool. Health probes: TCP, HTTP, HTTPS. Cross-region load balancer for geo-redundancy (GA).

**Q9.** Application Gateway: L7 load balancer. WAF (Web Application Firewall) with OWASP rule sets. URL-based routing (path /api → backend pool A, /web → pool B). Cookie-based session affinity. SSL offload. Autoscaling (v2 SKU). Also supports WebSocket and HTTP/2.

**Q10.** Azure Front Door: global L7 load balancer + CDN + WAF. Anycast-based entry. Routes to the nearest healthy backend. Split TCP (terminates TCP at the edge, new connection to backend over Microsoft backbone — reduces latency). DDoS protection built-in. Caching at the edge.

## Q11-Q20:

**Q11.** Azure Firewall Premium adds TLS inspection (terminates TLS, inspects payload for threats, re-encrypts), IDPS (signature-based intrusion detection/prevention with 67,000+ signatures), URL filtering (full URL path, not just FQDN), web categories. Deploy in hub VNet, UDRs on spokes force traffic through it.

**Q12.** Azure DDoS Protection: Basic (free, always-on, L3/L4 protection for all Azure resources). Standard (paid, adaptive tuning based on your traffic patterns, real-time telemetry, cost protection guarantee — Microsoft credits overage costs caused by a DDoS attack).

**Q13.** Azure Bastion: managed jump host. RDP/SSH to VMs over TLS from Azure portal — no public IP needed on VMs. Deployed in a dedicated AzureBastionSubnet (/26 minimum). Eliminates the need for a jump box VM.

**Q14.** Network Watcher: NSG flow logs (who talked to whom, allowed/denied — exported to Storage Account, analyzed with Traffic Analytics). Packet capture (capture traffic on a VM's NIC without SSH access). Connection troubleshoot (tests reachability between two VMs showing each hop). Next hop (shows which route a packet would take). IP flow verify (tests if NSG allows/denies a specific flow).

**Q15.** Azure Route Server: enables BGP peering between NVAs (network virtual appliances like Barracuda, Cisco CSR) and the Azure VNet. NVAs advertise routes via BGP, Route Server injects them into VNet's effective routes. Eliminates the need for UDRs when using NVAs — routes are learned dynamically.

**Q16.** AWS VPC comparison: VPC is similar to VNet. Security Groups (stateful, like NSG). NACLs (stateless, subnet-level, like a simpler NSG). Route Tables are explicit (Azure has system routes + UDR overrides). NAT Gateway for outbound internet. Transit Gateway = Virtual WAN equivalent. Direct Connect = ExpressRoute equivalent.

**Q17.** AWS Transit Gateway: central hub connecting VPCs, VPNs, Direct Connect. Supports route tables for segmentation. Equivalent to Azure Virtual WAN hub. Supports inter-region peering.

**Q18.** GCP VPC: globally scoped (one VPC spans all regions, subnets are regional). Firewall rules are global. No VNet peering needed within the same VPC — subnets in different regions communicate directly. Shared VPC allows multiple projects to use a common VPC.

**Q19.** Multi-cloud networking: connect Azure VNet to AWS VPC to GCP VPC. Options: site-to-site VPN between cloud gateways, Megaport/Equinix Cloud Exchange for private connectivity, third-party SD-WAN overlay (Aviatrix, Alkira). Key challenge: consistent security policy across clouds.

**Q20.** Cloud vs traditional security groups: cloud security groups are applied per-VM/NIC (micro-segmentation by default). Traditional firewalls are perimeter-based (north-south only). Cloud security groups are stateful (like stateful firewalls). Cloud NSGs can reference Service Tags (Azure-managed IP ranges) and ASGs (application groups) — more dynamic than static ACLs.

## Q21-Q50:

**Q21.** Hybrid DNS: on-prem DNS needs to resolve Azure Private DNS zones (e.g., privatelink.database.windows.net). Azure VMs need to resolve on-prem DNS names. Solution: Azure Private DNS Resolver with inbound endpoint (receives queries from on-prem) and outbound endpoint (forwards queries to on-prem DNS). Conditional forwarders on both sides.

**Q22.** Service Endpoints vs Private Endpoints: Service Endpoint adds an optimized route from the subnet to the PaaS service over Microsoft backbone — but the PaaS resource still has a public IP and uses its public endpoint. Private Endpoint creates a private IP in your VNet mapped to the PaaS resource — traffic never touches the public endpoint. Private Endpoint is more secure (no public exposure) but costs more (per-endpoint charge + data processing charge).

**Q23-Q50:** NSG best practices (deny-all default, use Service Tags, ASGs for role-based rules). Cost optimization (cross-AZ transfer: free in Azure unlike AWS). AKS networking modes (kubenet = basic, Azure CNI = Pod gets VNet IP, Azure CNI Overlay = Pod gets overlay IP with VNet node IPs). Azure Front Door vs Application Gateway (Front Door = global/edge, AppGW = regional). NAT Gateway (outbound SNAT with static public IPs). Azure Virtual Network Manager (centralized network policy management). Forced tunneling (all internet traffic routed to on-prem via VPN/ExpressRoute). Azure Firewall Manager (central policy for multiple firewalls). Troubleshooting effective routes, NSG flow log analysis, VPN tunnel debugging (IKE diagnostics), ExpressRoute circuit diagnostics (ARP table, route table), DNS failures, asymmetric routing in hub-spoke, UDR black holes, Private Endpoint DNS issues, peering connectivity, LB health probe failures. Design exercises: multi-region DR, 50-spoke enterprise, dual ExpressRoute + VPN, PCI-DSS compliant, AKS networking, landing zone, Azure VMware Solution, cloud firewall vs NVA decision, monitoring strategy, AZ-700 exam topics.

\newpage

# ANSIBLE EXPANDED ANSWERS (Q5-Q50)

## Q5. Ansible Inventory for Network Devices.

**Answer:** YAML inventory with network-specific variables:

```yaml
all:
  children:
    ios_devices:
      hosts:
        router1:
          ansible_host: 192.168.1.1
        router2:
          ansible_host: 192.168.1.2
      vars:
        ansible_network_os: cisco.ios.ios
        ansible_connection: ansible.netcommon.network_cli
        ansible_user: admin
        ansible_password: "{{ vault_network_password }}"
        ansible_become: true
        ansible_become_method: enable
        ansible_become_password: "{{ vault_enable_password }}"
```

Key: `ansible_connection: network_cli` (SSH-based CLI), not `ssh` (which expects a Linux target). `ansible_network_os` tells Ansible which platform module to use.

## Q6. Ansible Vault.

**Answer:** Encrypts sensitive data (passwords, keys) at rest. Encrypted vars files committed to Git safely.

```bash
ansible-vault create secrets.yml          # Create encrypted file
ansible-vault edit secrets.yml            # Edit
ansible-vault encrypt existing.yml        # Encrypt existing
ansible-playbook site.yml --ask-vault-pass  # Prompt for password
ansible-playbook site.yml --vault-password-file ~/.vault_pass  # File-based
```

In playbooks, reference vault-encrypted variables like any other variable. Vault supports multiple vault IDs for different environments (dev vs prod).

## Q7. Jinja2 Templates for Network Config.

**Answer:**

```jinja2
{# templates/interfaces.j2 #}
{% for intf in interfaces %}
interface {{ intf.name }}
  description {{ intf.description }}
  ip address {{ intf.ip }} {{ intf.mask }}
  {% if intf.shutdown | default(false) %}
  shutdown
  {% else %}
  no shutdown
  {% endif %}
!
{% endfor %}
```

```yaml
- name: Generate and push config
  cisco.ios.ios_config:
    src: interfaces.j2
```

## Q8. Roles Structure.

**Answer:**

```
roles/
  base_config/
    tasks/main.yml          # Task list
    templates/              # Jinja2 templates
    vars/main.yml           # Role-specific variables
    defaults/main.yml       # Default values (lowest precedence)
    handlers/main.yml       # Triggered actions (save config)
    meta/main.yml           # Dependencies
```

Roles promote reusability — `base_config` role applies NTP, syslog, SNMP, AAA to any device. Call via: `roles: [base_config, bgp_config, interfaces]`.

## Q9-Q50 (Key answers):

**Q9.** `cli_config` is generic (any network_os), `ios_config` is platform-specific (has `save_when`, `backup`, `before/after` options). Use platform-specific modules when available.

**Q10.** Facts gathering: `gather_facts: false` for network devices (default Linux fact gathering fails on network devices). Use `cisco.ios.ios_facts` to collect structured device facts (hostname, interfaces, VLANs, neighbors).

**Q11.** Idempotency: `ios_config` compares desired lines against running-config. Only pushes lines that are missing. `state: replaced` on resource modules replaces the entire section. `state: overridden` replaces across all instances.

**Q12.** Tags: `tags: [bgp, routing]` on tasks. Run only tagged tasks: `--tags bgp`. Skip: `--skip-tags dangerous`.

**Q13.** Handlers: triggered by `notify` on changed tasks. `handler: save_config` runs `copy running startup` only if the config was actually changed. Runs once at end of play regardless of how many tasks notified it.

**Q14.** Check mode: `--check` runs the playbook without making changes. For network modules, shows what WOULD change. `--diff` shows the config diff. Combine: `--check --diff` for safe pre-review.

**Q15.** Diff mode: `cisco.ios.ios_config` with `diff_against: running` shows the diff between desired config and running config. Essential for change review before applying.

**Q16.** Register and parsing: `register: output` captures task result. Access CLI output: `output.stdout[0]`. Parse with `regex_search`, `json_query`, or pipe to TextFSM. Use `assert` to validate parsed output.

**Q17.** Collections: `ansible-galaxy collection install cisco.ios cisco.nxos arista.eos junipernetworks.junos`. Pin versions in `requirements.yml`. Collections contain modules, plugins, roles.

**Q18.** Variable precedence (highest to lowest): extra-vars (-e), task vars, block vars, role params, play vars, host_vars, group_vars, inventory vars, role defaults. Extra-vars always win.

**Q19.** Loops: `loop: "{{ devices }}"` with `{{ item }}`. For network: loop over interfaces, VLANs, neighbors. `with_items` (legacy), `loop` (modern).

**Q20.** Conditionals: `when: ansible_network_os == 'cisco.ios.ios'` — run task only on IOS devices. `when: output.stdout[0] | regex_search('Established')` — conditional based on output.

**Q21.** Serial execution: `serial: 1` — process one host at a time. Critical for network changes — don't push config to all switches simultaneously. If something breaks, only one device is affected. `serial: "30%"` — process 30% at a time (rolling update).

**Q22.** Tower/AWX: web UI, REST API, RBAC (role-based access — network team can run networking playbooks only), scheduling, credential store (no passwords in playbooks), audit logging, job templates with surveys (prompted variables).

**Q23.** Dynamic inventory: pull inventory from NetBox/Nautobot API. `netbox.netbox.nb_inventory` plugin queries devices, populates inventory dynamically. Source of truth for all device info — no static inventory files to maintain.

**Q24.** Config backup automation: daily playbook runs `ios_command: show running-config`, writes output to timestamped files, commits to Git. Diff against yesterday's backup to detect unauthorized changes.

**Q25.** Compliance checking: define desired state (NTP servers, syslog config, SNMPv3 settings). Playbook gathers current state, compares, reports deviations. `ios_config` with `diff_against: intended` compares running-config against an intended config file.

**Q26-Q50:** Error handling (block/rescue/always for every change task), performance tuning (forks: 10-20 for network, pipelining: true, persistent_connection_idle_timeout: 120), event-driven Ansible (Event-Driven Ansible Controller watches for SNMP traps, triggers remediation playbooks), CI/CD integration (GitLab CI triggers ansible-playbook on MR merge), NETCONF with `netconf_config` module for YANG-based config (Juniper, IOS-XE with RESTCONF), Batfish pre-deployment validation (analyze config changes for correctness before pushing), Molecule for testing playbooks, AWX API for programmatic job execution, multi-vendor abstraction patterns (role per function with platform-specific task files included via `include_tasks: "{{ ansible_network_os }}.yml"`), troubleshooting (-vvv for verbose, check ansible_connection, verify SSH key auth, increase timeout for slow devices: `ansible_command_timeout: 60`).

\newpage

# PYTHON EXPANDED ANSWERS (Q6-Q50)

## Q6. REST API Interaction.

**Answer:**

```python
import requests
from requests.auth import HTTPBasicAuth

base_url = "https://10.0.0.1/restconf"
headers = {"Accept": "application/yang-data+json", "Content-Type": "application/yang-data+json"}
auth = HTTPBasicAuth("admin", "secret")

response = requests.get(
    f"{base_url}/data/Cisco-IOS-XE-native:native/interface",
    headers=headers,
    auth=auth,
    verify=False,
    timeout=30,
)
response.raise_for_status()
interfaces = response.json()
```

Always use `timeout`, `raise_for_status()`, and handle `requests.exceptions.ConnectionError`, `Timeout`, `HTTPError`.

## Q7. YANG/NETCONF with ncclient.

**Answer:**

```python
from ncclient import manager

with manager.connect(
    host="10.0.0.1",
    port=830,
    username="admin",
    password="secret",
    hostkey_verify=False,
    device_params={"name": "iosxe"},
) as m:
    config = m.get_config(source="running")
    print(config.xml)

    # Edit config
    edit_config = """
    <config>
      <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
        <hostname>ROUTER-01</hostname>
      </native>
    </config>
    """
    m.edit_config(target="running", config=edit_config)
```

## Q8. Async with scrapli.

**Answer:**

```python
import asyncio
from scrapli.driver.core import AsyncIOSXEDriver

async def get_version(host: str) -> str:
    device = {
        "host": host, "auth_username": "admin",
        "auth_password": "secret", "auth_strict_key": False,
        "transport": "asyncssh",
    }
    async with AsyncIOSXEDriver(**device) as conn:
        result = await conn.send_command("show version")
        return result.result

async def main():
    hosts = ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"]
    results = await asyncio.gather(*[get_version(h) for h in hosts])
    for host, result in zip(hosts, results):
        print(f"{host}: {result[:100]}")

asyncio.run(main())
```

10 devices in parallel vs 10 devices serial = 10x faster. scrapli supports async natively with asyncssh transport.

## Q9. Type Hints.

**Answer:**

```python
from dataclasses import dataclass

@dataclass
class Device:
    hostname: str
    ip: str
    platform: str
    site: str

def get_bgp_neighbors(device: Device) -> list[dict[str, str]]:
    """Return BGP neighbors for a device."""
    ...

def filter_established(neighbors: list[dict[str, str]]) -> list[dict[str, str]]:
    return [n for n in neighbors if n["state"] == "Established"]
```

Type hints enable IDE autocomplete, catch bugs before runtime (`mypy --strict`), and serve as documentation.

## Q10. Dataclasses for Network Models.

**Answer:**

```python
from dataclasses import dataclass, field

@dataclass
class Interface:
    name: str
    ip_address: str
    mask: str
    description: str = ""
    admin_state: str = "up"
    vrf: str = "default"

@dataclass
class Router:
    hostname: str
    mgmt_ip: str
    platform: str
    interfaces: list[Interface] = field(default_factory=list)

    def get_interface(self, name: str) -> Interface | None:
        return next((i for i in self.interfaces if i.name == name), None)
```

## Q11-Q50 (Key answers):

**Q11.** Pydantic for config validation: validates input data types, ranges, formats before pushing to devices. `BaseModel` with `Field(ge=1, le=4094)` for VLAN IDs, `IPvAnyAddress` for IPs. Catches misconfigurations before they reach the device.

**Q12.** Structured logging with `structlog`: `structlog.get_logger().info("command_sent", device="router1", command="show version", duration_ms=120)`. Outputs JSON — parseable by Elasticsearch/Splunk. Include device hostname, command, result, duration in every log entry.

**Q13.** Jinja2 in Python: `from jinja2 import Environment, FileSystemLoader`. Load templates from `templates/` directory, render with device-specific variables. `env.get_template("bgp.j2").render(neighbors=neighbors)`. Use for generating device configs from structured data.

**Q14.** Unit testing with pytest + mock: `@patch('netmiko.ConnectHandler')` to mock SSH connections. Test parsing logic without connecting to real devices. `assert parse_bgp_output(sample_output) == expected_result`. Test edge cases: empty output, error output, timeout.

**Q15.** NAPALM getters: `get_facts()` (hostname, model, serial, OS version), `get_interfaces()` (admin/oper state, speed, description), `get_bgp_neighbors()` (peer state, prefixes), `get_route_to('10.0.0.0/8')` (routing table lookup). All return consistent dicts regardless of vendor.

**Q16.** NAPALM config management: `load_merge_candidate(config=new_config)` → `compare_config()` (shows diff) → `commit_config()` (applies) or `discard_config()` (rollback). `rollback()` reverts to pre-commit state. Atomic commit-or-rollback — no partial config states.

**Q17.** Nornir: Python-native Ansible alternative. `InitNornir(config_file="nornir.yaml")` loads inventory. `nr.run(task=netmiko_send_command, command_string="show version")` executes across all hosts in parallel. Results object with per-host success/failure. Plugins: nornir_netmiko, nornir_napalm, nornir_scrapli.

**Q18.** PyATS/Genie: Cisco's test automation framework. `device.learn('bgp')` returns structured BGP state. `diff = Diff(before_bgp, after_bgp)` compares states. Parsers for 1500+ commands. `device.parse('show ip route')` returns structured dict without TextFSM. Excellent for pre/post change validation.

**Q19-Q25.** SNMP with pysnmp (GET/WALK/SET). NetBox API with pynetbox (`nb.dcim.devices.filter(site='dc1')`). ThreadPoolExecutor for parallel device access (`max_workers=20`). Environment variables for secrets (`os.environ['DEVICE_PASSWORD']`). CLI tools with `typer` or `click` for user-facing automation scripts.

**Q26-Q35.** Config backup with diff detection (hash comparison, Git commit on change). BGP health checker (connect, parse `show bgp summary`, alert on non-Established neighbors). Interface utilization reporter (poll SNMP counters, calculate bps). VLAN auditor (compare NetBox desired state vs device actual state, report drift). ACL parser (parse ACL text into structured objects, detect conflicts/shadows). Network diagram from CDP/LLDP (query all devices, build adjacency graph, output to draw.io XML or D3.js). Automated change window script (pre-check → snapshot → change → post-check → diff → rollback if failed). Multi-vendor config standardizer (parse configs from Cisco/Arista/Juniper into common model, identify deviations from baseline). Certificate expiry checker (connect to each device's HTTPS interface, check cert validity). IPAM script with NetBox API (allocate next available IP, create record, return to user).

**Q36-Q50.** Decorators for retry logic (`@retry(max_attempts=3, delay=5, exceptions=(NetmikoTimeoutException,))`). Context managers for device connections (`@contextmanager def connect(device): ...`). Generators for streaming large outputs (`yield` parsed results line by line instead of loading all into memory). Abstract base classes for multi-vendor (`class NetworkDevice(ABC): @abstractmethod def get_routes(self) -> list[Route]: ...`). Strategy pattern (pass platform-specific implementation at runtime). FastAPI for building automation APIs (`@app.post("/configure/bgp")` — REST endpoint that triggers config changes). Celery for async task queuing (long-running automation jobs). Docker for automation tools (containerize scripts with all dependencies). Rich library for beautiful CLI output (tables, progress bars, syntax highlighting). Pandas for tabular data analysis (interface utilization spreadsheets, capacity reports). Batfish for pre-deployment verification (analyze config offline, detect routing loops, verify ACL behavior). Suzieq for network observability (poll devices, store time-series data, query network state). containerlab for lab automation (define topology in YAML, spin up Arista/Cisco/Juniper virtual devices). CI/CD integration (GitLab CI runs `pytest` on automation code, then deploys via Ansible). Python packaging with `pyproject.toml` and `poetry` for reusable automation libraries.

