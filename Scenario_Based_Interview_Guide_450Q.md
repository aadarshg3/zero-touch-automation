---
title: "Network Engineer — Scenario-Based Interview Guide"
subtitle: "450 Real-World Scenarios · 9 Domains · Senior Level (8+ Years)"
author: "Prepared for Aadarsh Gupta"
date: "August 2026"
geometry: "margin=2cm"
fontsize: 11pt
toc: true
toc-depth: 2
---

\newpage

# SECTION 1: KUBERNETES NETWORKING SCENARIOS (50)

## S1. A developer reports that Pod A can reach Pod B on the same node, but Pod C on a different node is unreachable. What do you check?

**Answer:** Same-node Pod communication works, so the CNI's local veth pair setup and bridge/routing is functional. The problem is cross-node connectivity — the overlay or underlay routing between nodes.

**Investigation steps:**

1. Verify the CNI agent is healthy on both nodes: `kubectl -n kube-system get pods -o wide | grep calico` (or cilium). If the agent on Node 2 is CrashLooping, it can't program routes.

2. Check routes on Node 1: `ip route | grep <Node2-pod-CIDR>`. There should be a route to Node 2's pod CIDR via Node 2's IP (BGP mode) or via the VXLAN interface (overlay mode). If missing, the CNI hasn't programmed it.

3. For Calico BGP mode: `calicoctl node status` on both nodes — are BGP peers Established? If not, check if TCP 179 is blocked by a host firewall or cloud security group.

4. For VXLAN mode: `ip -d link show vxlan.calico` — is the VXLAN interface UP? `tcpdump -i eth0 port 4789` on Node 2 — are VXLAN packets arriving? If not, UDP 4789 may be blocked by the underlay network (cloud security group, physical firewall).

5. Test from the node itself: `ping <Pod-C-IP>` from Node 1. If this fails, it's a node-level routing issue, not a Pod issue.

**Root cause probabilities:** Cloud security group blocking UDP 4789 (40%), CNI agent crash (25%), BGP peering failure (20%), MTU issue with VXLAN overhead (15%).

**Cross-questions the interviewer would ask:**

- "How would you differentiate between a CNI issue and an underlay network issue?" — If `ping` between node IPs works but pod IPs don't, it's the overlay. If node IPs also fail, it's the underlay.
- "What if only SOME cross-node Pods fail?" — Check if the failing Pods are on a specific node. The issue may be node-specific (single CNI agent, single BGP peer).

---

## S2. After deploying a NetworkPolicy, all Pods in the namespace lose DNS resolution. What went wrong?

**Answer:** The NetworkPolicy likely specifies `policyTypes: [Egress]` without an explicit rule allowing DNS (UDP/TCP 53) to CoreDNS. Once any NetworkPolicy selects a Pod with Egress policy type, all egress becomes default-deny. DNS queries to CoreDNS are blocked.

**Fix:**

```yaml
egress:
  - to:
      - namespaceSelector: {}
        podSelector:
          matchLabels:
            k8s-app: kube-dns
    ports:
      - {protocol: UDP, port: 53}
      - {protocol: TCP, port: 53}
```

**Verification:**

```
kubectl exec -it <affected-pod> -- nslookup kubernetes.default
# Fails before fix, succeeds after
```

**Cross-questions:**

- "Why include TCP 53 and not just UDP 53?" — DNS uses UDP by default, but falls back to TCP for responses >512 bytes (large TXT records, DNSSEC). Blocking TCP 53 causes intermittent failures.
- "What if CoreDNS runs in kube-system but the policy is in namespace 'app'?" — The `namespaceSelector: {}` matches ALL namespaces, including kube-system. Without it, `podSelector` only matches within the same namespace — CoreDNS would be unreachable.
- "What's the most common NetworkPolicy mistake?" — Exactly this: forgetting DNS egress when specifying Egress policyType.

---

## S3. Your Ingress Controller returns 502 Bad Gateway for a specific path (/api) but the root path (/) works fine. Troubleshoot.

**Answer:** 502 means the Ingress Controller (e.g., NGINX) connected to the backend Service but the backend didn't respond properly.

**Investigation:**

1. Check the Ingress definition: `kubectl get ingress <name> -o yaml`. Verify `/api` maps to the correct Service and port.

2. Check the backend Service has endpoints: `kubectl get endpoints <api-svc>`. If empty, the Service's label selector doesn't match any running Pods — the backend is effectively nonexistent.

3. If endpoints exist, check the Pods directly: `kubectl exec -it <ingress-controller-pod> -- curl http://<api-pod-ip>:<targetPort>/api`. If this times out, the Pod isn't listening on that port for that path.

4. Check targetPort: the Service might be pointing to port 80 but the container listens on 8080 for /api. Verify: `kubectl describe svc <api-svc>` — check `TargetPort`.

5. Check readiness probes: `kubectl describe pod <api-pod>` — if the readiness probe is failing, the Pod is removed from Endpoints. The Pod is running but not "ready" so the Service excludes it.

6. Check Ingress Controller logs: `kubectl logs <ingress-controller-pod> | grep 502` — shows upstream connection details (timeout, connection refused, reset).

**Root cause probabilities:** Readiness probe failing (35%), wrong targetPort (25%), no matching Pods for selector (20%), backend Pod crash-looping (15%), path not handled by the app (5%).

**Cross-questions:**

- "What's the difference between 502 and 503?" — 502: controller reached backend but got invalid response. 503: controller can't reach any backend (all endpoints unhealthy or none exist).
- "How would you test bypassing the Ingress entirely?" — `kubectl port-forward svc/<api-svc> 8080:80` then `curl localhost:8080/api` — tests the Service directly.

---

## S4. A team reports their application experiences 5-second DNS lookup delays intermittently. The cluster uses CoreDNS. Diagnose.

**Answer:** Classic conntrack race condition with UDP DNS. When a Pod sends a DNS query, kube-proxy DNATs the packet (destined for CoreDNS ClusterIP) to a CoreDNS Pod IP. The DNAT creates a conntrack entry. Simultaneously, the conntrack garbage collector may delete the entry if it's deemed stale (UDP has no explicit connection state). The response from CoreDNS arrives but doesn't match any conntrack entry — it's dropped. The application's resolver waits 5 seconds (the default `resolv.conf` timeout) before retrying.

**Evidence:** The 5-second delay exactly matches the DNS resolver timeout. It's intermittent because the race condition depends on timing.

**Fixes (in order of effectiveness):**

1. Deploy `node-local-dns` DaemonSet — caches DNS at each node, eliminates the conntrack DNAT path for DNS queries. Best solution.

2. Force DNS over TCP: set `use-vc` option in Pod's dnsConfig — TCP conntrack is more reliable. Adds slight latency.

3. Increase conntrack timeout for DNS: `sysctl net.netfilter.nf_conntrack_udp_timeout_stream=180`.

**Verification:**

```
# Check if node-local-dns is deployed
kubectl -n kube-system get ds node-local-dns

# Monitor DNS latency
kubectl exec -it <pod> -- time nslookup kubernetes.default
```

**Cross-questions:**

- "Why does this only affect UDP and not TCP?" — TCP has explicit connection state (SYN/SYN-ACK/FIN). Conntrack tracks the full handshake. UDP is stateless — conntrack uses timeouts to guess connection state, creating the race.
- "Would switching to Cilium fix this?" — Yes, if Cilium replaces kube-proxy. Cilium's eBPF socket-level load balancing doesn't use conntrack for Service DNAT.

---

## S5. You're deploying Calico in a cloud environment but Pods can't communicate across nodes. On-prem the same config works. Why?

**Answer:** On-prem, Calico BGP mode works because the physical network routes Pod CIDRs (either via BGP peering with ToR switches or via static routes). In cloud (AWS/Azure/GCP), the virtual network doesn't know about Pod CIDRs. When Node 1 sends a packet with source=PodIP to Node 2, the cloud fabric drops it — the source IP isn't a known VPC/VNet IP.

**Fix:** Switch Calico to VXLAN mode (or IPIPMode). This encapsulates Pod traffic inside node-to-node UDP/IP packets. The cloud network only sees node IPs (which it knows about) as source/destination.

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: default-ipv4-ippool
spec:
  cidr: 10.244.0.0/16
  vxlanMode: Always          # Changed from Never (BGP) to Always (VXLAN)
  natOutgoing: true
```

**Cross-questions:**

- "Is there a way to use BGP in the cloud?" — In AWS, you can disable source/destination check on EC2 instances and run BGP. But it's fragile. GCP supports custom routes that can be injected. Azure has UDRs. But VXLAN is simpler and portable across clouds.
- "What's the CrossSubnet option?" — `vxlanMode: CrossSubnet` uses BGP for Pods on the same L2 subnet (same availability zone) and VXLAN only when crossing subnets. Best of both worlds — native routing where possible, encapsulation only where needed.

---

## S6. After upgrading Cilium, you notice kube-proxy iptables rules are still present alongside Cilium's eBPF. Is this a problem?

**Answer:** Yes. If both kube-proxy and Cilium are active, Service traffic may be processed twice — once by iptables (kube-proxy) and once by eBPF (Cilium). This can cause: duplicate DNAT, conntrack conflicts, and unpredictable routing behavior.

**Investigation:**

```
kubectl -n kube-system get ds kube-proxy    # Is kube-proxy still running?
cilium status | grep KubeProxyReplacement  # Should show "True" or "Strict"
iptables-save | grep -c KUBE-SVC           # Count kube-proxy rules (should be 0)
```

**Fix:** (1) Delete the kube-proxy DaemonSet: `kubectl -n kube-system delete ds kube-proxy`. (2) Flush stale iptables rules: `iptables-save | grep -v KUBE | iptables-restore`. (3) Verify Cilium has `kubeProxyReplacement: true` in its ConfigMap. (4) Restart Cilium agents: `kubectl -n kube-system rollout restart ds cilium`.

**Cross-questions:**

- "How do you verify Cilium is handling all Service traffic?" — `cilium service list` should show all ClusterIPs. `cilium bpf lb list` should show backend mappings. `iptables-save | grep KUBE-SVC | wc -l` should return 0.
- "What if you can't remove kube-proxy because other components depend on it?" — Run Cilium in `kubeProxyReplacement: partial` — it only replaces specific features while kube-proxy handles the rest.

---

## S7. A Pod can reach external internet (google.com) but cannot reach Services in another namespace. What's wrong?

**Answer:** If internet works, Pod's egress and routing are fine. Cross-namespace Service failure suggests either: (1) NetworkPolicy blocking cross-namespace traffic, or (2) DNS resolution failing for the cross-namespace Service name.

**Investigation:**

1. Test DNS: `kubectl exec -it <pod> -- nslookup <svc>.<target-ns>.svc.cluster.local`. If this fails → DNS issue (wrong service name, CoreDNS misconfiguration). If it resolves → connectivity issue.

2. Test connectivity: `kubectl exec -it <pod> -- curl <resolved-ClusterIP>:<port>`. If this times out → NetworkPolicy is blocking the traffic.

3. Check NetworkPolicies in the target namespace: `kubectl get networkpolicy -n <target-ns>`. If a policy exists with `podSelector` matching the target Pods and `ingress` rules that don't include the source namespace → blocked.

**Fix for NetworkPolicy:** Add `namespaceSelector` to the ingress rule:

```yaml
ingress:
  - from:
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: source-ns
        podSelector:
          matchLabels:
            app: allowed-client
```

**Cross-questions:**

- "The developer says 'it worked yesterday.' What changed?" — Check recent NetworkPolicy changes: `kubectl get networkpolicy -n <target-ns> -o yaml | grep creationTimestamp`. Also check if labels on the source Pods changed (breaking a podSelector match).
- "What if the developer uses just the Service name without the namespace?" — `<svc>` without the namespace suffix resolves within the same namespace. For cross-namespace: `<svc>.<ns>` or `<svc>.<ns>.svc.cluster.local`.

---

## S8. Your monitoring shows that one Kubernetes node handles 70% of all Service traffic while three other nodes handle 10% each. What's causing this imbalance?

**Answer:** Several possible causes:

1. **externalTrafficPolicy: Local** with uneven Pod distribution: If most backend Pods are scheduled on one node, and the external LB uses `externalTrafficPolicy: Local`, it sends proportionally more traffic to that node. The LB health-checks NodePorts — nodes with more Pods are "heavier."

2. **IPVS source hashing:** If kube-proxy uses IPVS with `sh` (source hash) algorithm, clients from similar IP ranges hash to the same backend. A few large clients can skew distribution.

3. **Client-side caching of DNS:** If the Service uses ExternalDNS/headless and clients cache the first Pod IP they resolve, traffic sticks to one Pod.

**Investigation:**

```
# Check Pod distribution
kubectl get pods -l app=<workload> -o wide    # Which nodes have Pods?

# Check externalTrafficPolicy
kubectl get svc <svc> -o jsonpath='{.spec.externalTrafficPolicy}'

# Check kube-proxy mode and algorithm
kubectl -n kube-system get cm kube-proxy -o yaml | grep -A5 ipvs
```

**Fix:** Redistribute Pods via `topologySpreadConstraints` (ensures even spread across nodes). If using IPVS, switch to `rr` (round-robin). If using headless Service, client must not cache DNS (set low TTL).

---

## S9. After scaling a Deployment from 3 to 50 replicas, some Pods get stuck in ContainerCreating with the event "failed to allocate for range: no IP addresses available."

**Answer:** The node's Pod CIDR is exhausted. If the node has a /24 (254 usable IPs) and 50 new Pods land on this node (plus existing Pods from other workloads), it exceeds capacity.

**Investigation:**

```
kubectl describe pod <stuck-pod>                   # Event shows IPAM failure
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.podCIDR}{"\n"}{end}'
# Check how many Pods are on the node
kubectl get pods --field-selector spec.nodeName=<node> | wc -l
```

**Fixes:** (1) Use Calico IPAM with dynamic block allocation instead of host-local (blocks assigned on demand, can borrow from other nodes). (2) Increase node CIDR mask size (`--node-cidr-mask-size /23` = 510 IPs per node). (3) Add more nodes so Pods spread. (4) Set `maxPods` per node in kubelet config to prevent overloading.

**Cross-questions:**

- "How does this differ from cloud CIDR exhaustion?" — In Azure CNI mode, Pod IPs come from the VNet subnet, not a Kubernetes-managed CIDR. If the Azure subnet is /24, you can only create 251 Pods across ALL nodes in that subnet. This is a common Azure scaling surprise.
- "How would you proactively monitor for this?" — Alert on `kubelet_node_ip_addresses_available` metric or Calico IPAM utilization: `calicoctl ipam show`.

---

## S10. A gRPC application behind a ClusterIP Service experiences load imbalance — one Pod gets 90% of requests.

**Answer:** gRPC uses HTTP/2, which multiplexes all requests over a single long-lived TCP connection. kube-proxy's DNAT happens at connection time — once the TCP connection is established to a backend Pod, ALL requests on that connection go to the same Pod. Unlike HTTP/1.1 (where each request is a new TCP connection and gets independently load-balanced), HTTP/2 pins all traffic to one backend.

**Fixes:**

1. **Headless Service + client-side load balancing:** Use a headless Service so DNS returns all Pod IPs. Configure the gRPC client to use `dns:///` resolver with round-robin pick_first policy. The client distributes RPCs across all Pods.

2. **Service mesh (Istio/Linkerd):** The sidecar proxy understands L7 gRPC and load-balances per-request, not per-connection.

3. **Cilium L7 load balancing:** Cilium can intercept at L7 and distribute gRPC requests across backends without a sidecar.

**Cross-questions:**

- "Why doesn't increasing replicas help?" — More replicas doesn't matter if all connections pin to one Pod. The issue is connection-level vs request-level balancing.
- "How does Istio solve this?" — Envoy sidecar terminates the client's HTTP/2 connection and opens separate HTTP/2 connections to each backend. Requests are distributed per-RPC across these connections.

---

## S11-S25 (Continued Kubernetes Scenarios):

## S11. Your cluster has 200 Services. After migrating from iptables to IPVS mode kube-proxy, some Services become unreachable. What broke?

**Answer:** IPVS mode requires ClusterIPs to be bound to a dummy interface (`kube-ipvs0`) on each node. If the IPVS kernel modules aren't loaded (`ip_vs`, `ip_vs_rr`, `ip_vs_wrr`, `ip_vs_sh`, `nf_conntrack`), kube-proxy falls back to iptables mode silently OR fails to create virtual servers. Check: `lsmod | grep ip_vs`. Also, if `strictARP: true` is needed for MetalLB but wasn't set, ARP responses for ClusterIPs may leak to the network.

```
ipvsadm -Ln | wc -l          # Should show entries for all Services
kubectl -n kube-system logs <kube-proxy-pod> | grep -i "ipvs\|error"
lsmod | grep ip_vs
```

---

## S12. A Pod's /etc/resolv.conf shows ndots:5 and developers complain that external API calls are slow (adds 200ms to every call). Fix it without changing the application.

**Answer:** Every external hostname like `api.stripe.com` (2 dots < 5) triggers 4 failed DNS lookups (appending search domains) before the real query. Solution at the Pod spec level:

```yaml
spec:
  dnsConfig:
    options:
      - name: ndots
        value: "2"
```

This reduces unnecessary queries. `api.stripe.com` has 2 dots ≥ ndots:2, so it's queried as-is first. Internal names like `my-svc` (0 dots) still get search domain expansion. Verify: `kubectl exec <pod> -- time nslookup api.stripe.com` — should drop from ~1s to <50ms.

---

## S13. You need to allow a specific Pod to reach an external database at 10.200.50.100:5432, but deny all other egress. Write the policy and explain each part.

**Answer:**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-egress-only
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Egress]
  egress:
    - to:                              # Rule 1: Allow DNS
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - {protocol: UDP, port: 53}
        - {protocol: TCP, port: 53}
    - to:                              # Rule 2: Allow external DB
        - ipBlock:
            cidr: 10.200.50.100/32
      ports:
        - {protocol: TCP, port: 5432}
```

**Explanation:** Rule 1 allows DNS (without this, the Pod can't resolve anything). Rule 2 allows egress to the exact DB IP on port 5432 only. Everything else is denied because `policyTypes: [Egress]` makes all egress default-deny once any rule is applied.

**Cross-question:** "What if the DB IP changes?" — Use CiliumNetworkPolicy with FQDN-based egress: `toFQDNs: [{matchName: "db.internal.company.com"}]`. Cilium resolves the FQDN and dynamically updates the allowed IP set.

---

## S14. A Kubernetes cluster on bare metal needs external LoadBalancer IPs but has no cloud provider. The team asks you to implement this. Describe your approach.

**Answer:** Deploy MetalLB. Decision: L2 mode vs BGP mode.

**If the network team can't configure BGP on the ToR switches** → L2 mode. MetalLB's speaker responds to ARP for the Service IP. Single-node handles all traffic for that IP (no true load balancing at L2), but failover works (another node takes over ARP if the leader fails). Simpler, no switch config needed.

**If ToR switches support BGP** → BGP mode. Each node peers with the ToR via eBGP and announces Service IPs as /32. ECMP across all nodes — true load balancing. Requires switch configuration (BGP neighbor, prefix acceptance).

**Implementation (L2 mode):**

```yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: production
  namespace: metallb-system
spec:
  addresses: ["192.168.1.240-192.168.1.250"]
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: l2
  namespace: metallb-system
```

**Verification:** Create a Service with `type: LoadBalancer`. Check `kubectl get svc` — EXTERNAL-IP should be assigned from the pool. `arping 192.168.1.240` — should get response from the speaker node.

---

## S15. After a node reboot, Pods on that node can't reach any Service ClusterIPs. Other nodes are fine. Pods on the rebooted node can ping external IPs.

**Answer:** kube-proxy on the rebooted node hasn't reprogrammed its iptables/IPVS rules yet, or it failed to start.

**Check:**

```
kubectl -n kube-system get pods -o wide | grep kube-proxy   # Is it Running on this node?
kubectl -n kube-system logs <kube-proxy-pod-on-this-node>    # Any errors?
# If iptables mode:
iptables-save | grep KUBE-SVC | wc -l                       # Should be >0
# If IPVS mode:
ipvsadm -Ln | wc -l                                         # Should match Service count
```

If kube-proxy failed to start (image pull failure, OOMKilled), no Service rules exist on this node. Pods can reach external IPs (direct routing works) but can't reach ClusterIPs (no DNAT rules). Fix: resolve the kube-proxy Pod issue (check events, resources, image availability).

---

## S16-S25 (Additional Kubernetes Scenarios):

**S16.** "A developer deployed a CronJob that creates thousands of completed Pods. CoreDNS starts OOMKilling. Why?" — Each Pod creates EndpointSlice entries while running. The churn from thousands of short-lived Pods generates massive EndpointSlice updates. CoreDNS watches these and its memory grows. Fix: set `ttlSecondsAfterFinished: 300` on the CronJob to auto-delete completed Pods.

**S17.** "You're asked to implement network segmentation between dev and prod namespaces without a service mesh." — Default-deny NetworkPolicy in both namespaces. No cross-namespace ingress/egress rules. Add explicit rules only for the services that must cross boundaries (e.g., shared logging). Label namespaces: `kubectl label ns prod env=prod`, use `namespaceSelector` in policies.

**S18.** "A Pod keeps getting a different IP every time it restarts, breaking a stateful application that uses IP-based session affinity." — Use a StatefulSet with a headless Service for stable DNS names. Or configure `sessionAffinity: ClientIP` on the Service (kube-proxy pins client-to-backend for a configurable timeout). Or use a fixed IP annotation with Calico: `cni.projectcalico.org/ipAddrs: '["10.244.1.100"]'`.

**S19.** "After enabling Cilium's kube-proxy replacement, NodePort Services stop working from external clients." — Cilium needs explicit NodePort configuration. Check `cilium status` for `NodePort` status. Ensure `nodePort.enabled: true` in Cilium's Helm values. If using `Direct Server Return (DSR)` mode, verify that the return path doesn't break (DSR skips SNAT, so the external client sees the Pod IP as source — may be dropped by stateful firewalls expecting the node IP).

**S20.** "A multi-tenant cluster needs tenant isolation so Tenant A's Pods can never reach Tenant B's Pods, even if someone misconfigures a NetworkPolicy." — Namespace-per-tenant with default-deny NetworkPolicy (cluster-admin managed, not tenant-editable). CiliumClusterwideNetworkPolicy with `endpointSelector` matching tenant labels. Consider separate VRFs or separate clusters for strongest isolation.

**S21.** "An application using a headless Service for database discovery suddenly can't discover new replicas added by an HPA scale-up." — DNS caching. The application cached the DNS response from when there were 3 replicas. New replicas have new DNS A records, but the cache hasn't expired. Fix: reduce DNS TTL (CoreDNS `cache` TTL setting), or have the application re-resolve DNS periodically.

**S22.** "You're debugging a NetworkPolicy but can't tell which policy is blocking traffic." — With Calico: `calicoctl get workloadendpoint -o yaml` shows applied policies. With Cilium: `hubble observe --to-pod <target> --verdict DROPPED` shows exact policy that denied. `cilium policy get` lists all policies. `kubectl describe networkpolicy -n <ns>` shows which Pods are selected.

**S23.** "Pods on a GPU node can't communicate with Pods on regular nodes. The GPU node uses a different CNI plugin (SR-IOV with Multus)." — Multus provides additional interfaces but the primary interface (`eth0`) should still be managed by the cluster's main CNI (Calico/Cilium). If the primary CNI isn't configured on the GPU node (perhaps Multus replaced it entirely instead of adding to it), cross-node communication breaks. Ensure Multus is configured as a meta-plugin that chains with the primary CNI, not replaces it.

**S24.** "Your cluster has 5000 Services and you notice iptables rule updates take 15 seconds, during which new connections may fail." — iptables mode kube-proxy rewriting the entire ruleset atomically. At 5000 Services with multiple backends each, the iptables-save/restore takes seconds. During this window, rules are briefly inconsistent. Fix: migrate to IPVS mode (`mode: ipvs` in kube-proxy ConfigMap) or Cilium eBPF (O(1) updates). IPVS handles 10K+ Services without this problem.

**S25.** "A Service with `externalTrafficPolicy: Local` returns connection refused from 2 of 4 nodes. The other 2 nodes work." — The 2 failing nodes don't have any backend Pods. With `Local` policy, nodes without Pods reject traffic on the NodePort. The external LB must health-check the NodePort and remove nodes without backends. If the LB doesn't health-check, clients reaching the wrong nodes get connection refused. Fix: configure LB health checks, or ensure Pods are distributed across all nodes (DaemonSet or `topologySpreadConstraints`).

## S26-S50 (Continued Kubernetes Scenarios):

**S26.** "A canary deployment sends 10% of traffic to v2 Pods, but v2 Pods receive 50% because there's 1 v2 Pod and 1 v1 Pod." — kube-proxy distributes equally per-Pod, not by weight. 2 Pods = 50/50 regardless of desired ratio. Fix: use Gateway API HTTPRoute with `weight` on backendRefs, or Istio VirtualService with weighted destinations. These do L7 traffic splitting at the Ingress/mesh level.

**S27.** "A Pod running tcpdump on eth0 inside the container shows packets arriving, but the application isn't receiving them." — Application may be listening on `127.0.0.1` (localhost only), not `0.0.0.0` (all interfaces). Packets arriving on `eth0` to the Pod IP are not routed to localhost. Fix: bind application to `0.0.0.0`. Verify: `ss -tlnp` inside the Pod — check the listening address.

**S28.** "After adding a new worker node, Pods scheduled there can't reach the internet. All other nodes work." — The new node is missing the NAT/masquerade rule. Check `iptables -t nat -L POSTROUTING -n -v` — there should be a MASQUERADE rule for Pod CIDR. If the CNI agent didn't start properly, this rule isn't created. Also check: does the node have a default route? `ip route show default`.

**S29.** "CoreDNS Pods keep OOMKilling. The cluster has 500 namespaces and 3000 Services." — CoreDNS memory usage scales with the number of watched objects. At 3000 Services, the in-memory cache and watch stream are substantial. Fix: increase CoreDNS memory limits, add more replicas (HPA based on memory/CPU), enable `lameduck` for graceful termination, consider enabling `autopath` plugin to reduce query amplification from ndots:5.

**S30.** "A team wants to expose a TCP database (port 5432) externally. Ingress only handles HTTP. What's the solution?" — Use Gateway API TCPRoute (if the controller supports it), or a Service type LoadBalancer directly (no Ingress needed for non-HTTP). If using NGINX Ingress, configure TCP/UDP exposure via `tcp-services` ConfigMap.

**S31.** "A Service ClusterIP is reachable from Pods but not from a host process on the same node." — Host processes bypass kube-proxy's Pod-level hooks. In Cilium's socket-level LB, only Pods have eBPF attached. Host processes need iptables rules or `hostPort` configuration. Check if `bpf.masquerade` and `hostReachableServices` are enabled in Cilium config.

**S32.** "Two teams deployed Services with the same name in different namespaces. One team's Pods are reaching the wrong Service." — DNS resolution: a Pod in namespace A querying `my-svc` gets `my-svc.A.svc.cluster.local` (correct). If someone hardcoded `my-svc.B.svc.cluster.local`, they'd reach namespace B's Service. Check application config for hardcoded FQDNs. Verify: `kubectl exec <pod-in-A> -- nslookup my-svc`.

**S33.** "After deploying Cilium CiliumNetworkPolicy with L7 HTTP rules, latency increased by 5ms per request." — L7 inspection requires Cilium to proxy through its Envoy instance. The packet goes: Pod → eBPF → Envoy (L7 inspect) → eBPF → destination. The Envoy hop adds latency. If L7 isn't needed for this traffic, use standard L3/L4 NetworkPolicy instead. If L7 is required, tune Envoy resources and consider co-locating the Envoy proxy.

**S34.** "A StatefulSet with 3 replicas and a headless Service — Pod-0 can reach Pod-1 by DNS name, but Pod-2 can't reach Pod-0." — Check if Pod-0 is in CrashLoop or NotReady — its DNS record would be removed from the headless Service's endpoint list. `kubectl get endpoints <headless-svc>` — is Pod-0's IP listed? If the Pod is terminating, its DNS entry is removed even though the Pod is still running. Check `publishNotReadyAddresses: true` on the Service if you need DNS entries for non-ready Pods.

**S35.** "An Ingress with TLS terminates correctly for one host but shows 'fake certificate' for another." — The Secret referenced for the second host either doesn't exist, doesn't contain a valid cert for that domain, or the Ingress Controller loaded a default/self-signed cert. Check: `kubectl get secret <tls-secret> -o yaml | grep tls.crt` — decode and verify the CN/SAN matches the hostname. Check Ingress Controller logs for cert loading errors.

**S36.** "You're asked to implement rate limiting per client IP at the Ingress level." — NGINX Ingress: use annotations `nginx.ingress.kubernetes.io/limit-rps: "10"` (10 requests per second per client IP). For finer control, use `limit-connections` and `limit-rpm`. The annotation creates an NGINX limit_req zone keyed by `$binary_remote_addr`. Requires `externalTrafficPolicy: Local` to preserve client IP — otherwise all traffic appears from a single node IP.

**S37.** "A team runs a batch job that opens 50,000 connections to a Service in 10 seconds. The Service becomes unreachable for everyone." — conntrack table exhaustion on the node. 50K connections + existing connections exceed `nf_conntrack_max`. New connections are dropped. Fix: increase conntrack_max (`sysctl net.netfilter.nf_conntrack_max=524288`), or use Cilium which doesn't use conntrack for Service DNAT. Also consider rate-limiting the batch job.

**S38.** "Pods in one AZ have 2ms latency to a Service, but Pods in another AZ have 15ms." — Cross-AZ traffic adds latency and costs. Enable Topology Aware Routing: `service.kubernetes.io/topology-mode: Auto` annotation on the Service. kube-proxy prefers same-zone backends when available.

**S39.** "A Pod needs to reach an external service at a specific FQDN, but the corporate DNS server returns a split-horizon response (internal IP) instead of the public IP." — The Pod's DNS resolves through CoreDNS which forwards to the corporate DNS. Corporate DNS returns the internal IP because it sees the query as "internal." Fix: configure CoreDNS to use a specific upstream for that domain (conditional forwarding): add a `forward` directive in the Corefile for that domain pointing to a public DNS server.

**S40.** "You need to implement a network policy that allows traffic from Pods with a specific ServiceAccount, not just labels." — Standard NetworkPolicy doesn't support ServiceAccount-based selection. Use CiliumNetworkPolicy with `fromEntities: ["cluster"]` and identity-based matching, or Istio AuthorizationPolicy which natively supports ServiceAccount-based rules.

**S41-S50.** Additional scenarios covering: cert-manager ACME challenge failing (port 80 blocked by NetworkPolicy), Service mesh sidecar injection breaking init container network setup, kubelet failing to invoke CNI after node disk pressure event, IPAM conflict between two Calico IPPools with overlapping CIDRs, cross-cluster service discovery with ClusterMesh failing due to cluster ID conflict, debugging a network-intensive Pod that's being CPU-throttled (eBPF processing on the node's CPU counts against the Pod's cgroup), migrating from Flannel to Calico without Pod restart (dual-CNI transition), Cilium Hubble showing "identity unknown" for external traffic (needs CiliumNode resources), implementing egress gateway for a compliance requirement (all outbound traffic must come from a known IP), designing network architecture for a multi-tenant SaaS platform on Kubernetes (namespace isolation + NetworkPolicy + egress control per tenant).


\newpage

# SECTION 2: BGP SCENARIOS (50)

## S1. Your eBGP neighbor is stuck in Active state. Both sides show the correct peer IP. What's wrong?

**Answer:** Active = TCP connection attempts failing. Ordered checks: (1) `ping <peer-ip>` — if fails, routing issue to peer IP. Check `show ip route <peer-ip>`. (2) `telnet <peer-ip> 179` — tests if TCP 179 is open. If connection refused → BGP process not running on peer. If timeout → firewall blocking TCP 179. (3) If using loopbacks: is `update-source Loopback0` configured? Is `ebgp-multihop` set? The loopback must be reachable via IGP. (4) MD5 mismatch — causes silent RST. `debug ip bgp` shows "MD5 digest mismatch." Check: `show bgp neighbors <ip> | include password`. (5) Source interface down — `show ip interface brief` on the interface used for peering.

**Cross-questions:** "The peer is on a /30 link but you're peering via loopbacks. What's the advantage?" — If the physical link fails but an alternate path exists (second link, backup route), the loopback peering survives. Physical interface peering dies with the link.

---

## S2. A remote site advertises 10.0.0.0/8 but traffic from your network to 10.1.1.0/24 is going to the wrong site. Why?

**Answer:** Longest prefix match. If another site advertises 10.1.1.0/24 specifically, that /24 wins over /8 even if the /8 has a shorter AS-PATH. Check `show bgp 10.1.1.0/24` — you'll see both the /8 covering route and the specific /24. The /24 is installed in the RIB because of longest-match. If the /24 is a hijack or a leak, filter it: `ip prefix-list DENY-LEAK seq 5 deny 10.1.1.0/24`, `ip prefix-list DENY-LEAK seq 10 permit 0.0.0.0/0 le 32`.

---

## S3. After an ISP change, inbound traffic still routes through the old ISP despite correct BGP advertisements from the new ISP. Diagnose.

**Answer:** Your outbound routing works (LOCAL_PREF controls that). Inbound is controlled by how the internet sees your prefix. Issues: (1) The old ISP is still advertising your prefix — contact them to withdraw. (2) AS-PATH from the new ISP is longer than the cached path via old ISP — peers prefer the shorter path. Fix: stop prepending on new ISP, add prepends on old ISP (if they're still advertising). (3) Propagation delay — BGP convergence across the internet takes minutes to hours. Use a looking glass (he.net/bgp) to check how your prefix looks from external ASes. (4) Some ISPs cache routes aggressively — send a BGP route refresh or wait for natural reconvergence.

---

## S4. Your BGP session keeps flapping every 30-45 minutes. Each time, the hold timer expires. What do you investigate?

**Answer:** Hold timer expires when 3 consecutive keepalives are missed (default: 60s keepalive, 180s hold). Possible causes: (1) Intermittent connectivity — flapping physical link, SFP issue. Check `show logging` for interface up/down. (2) CPU overload — router too busy to process keepalives. `show processes cpu sorted`. BGP keepalives are low priority. (3) QoS policer dropping BGP packets — if BGP traffic hits a rate limiter on the control plane. Check CoPP (Control Plane Policing). (4) MTU issue — if the BGP UPDATE is large (many prefixes) and exceeds the link MTU, the TCP session stalls. Check `show ip bgp neighbor <ip> | include hold`.

**Fix:** Enable BFD (detects failure in milliseconds, faster than hold timer). Tune hold/keepalive timers: `neighbor X.X.X.X timers 10 30` (10s keepalive, 30s hold). Check CoPP policy to ensure BGP isn't being rate-limited.

---

## S5. You receive a full BGP table from two ISPs. Your router's memory usage is at 95% and climbing. How do you address this immediately?

**Answer:** Immediate: (1) Stop accepting full tables: `neighbor X.X.X.X prefix-list DEFAULT-ONLY in` — accept only default route. This drops 900K+ routes instantly. (2) If you need partial routes: accept only customer and peer routes, not full transit. `neighbor X.X.X.X route-map PARTIAL-ROUTES in` matching communities for customer/peer routes + default.

**Long-term:** Upgrade hardware (more RAM), optimize RIB with `bgp bestpath cost-community ignore` if not needed, check if both ISPs' full tables are necessary (often one full + one default is sufficient for traffic engineering), or use a route server instead of full table on each router.

**Cross-questions:** "How much memory does a full BGP table consume?" — ~2-4GB for RIB with multiple paths. Each prefix needs ~400-600 bytes. With 2 ISPs providing 1M prefixes each (with some overlap), you need at least 4GB for BGP alone. "What happens if the router runs out of memory?" — BGP process crashes, routes are withdrawn, network goes down. Some platforms have OOM protection that kills BGP before the entire system fails.

---

## S6. A customer reports that their prefix is being hijacked — traffic from certain regions is going to an unauthorized AS. How do you investigate and mitigate?

**Answer:** (1) Check RIPE RIS/RouteViews or bgp.tools — search for the customer's prefix. Identify which ASes are originating it. If an unauthorized AS appears, it's a hijack. (2) Check if the customer has RPKI ROA published. If yes, the hijacking route should be marked Invalid by RPKI-validating networks and dropped. If no ROA exists, the hijack is indistinguishable from a legitimate announcement. (3) Mitigation: customer should publish ROA immediately (via their RIR). Notify the hijacking AS's upstream providers. If the hijacker is advertising a more-specific prefix (/24 vs customer's /22), the customer should also advertise the /24s to win longest-match.

**Cross-question:** "What if the customer can't break their /22 into /24s?" — Many ISPs filter prefixes longer than /24 (won't accept /25s). If the customer advertises /22 and the hijacker advertises /24, the hijacker wins for that /24 portion. The only defense is RPKI — the /24 with an Invalid ROA should be dropped by validating networks.

---

## S7. After configuring a Route Reflector, some routes are missing from client routers that were visible before. What happened?

**Answer:** The Route Reflector only reflects the BEST path. Before RR (full mesh), each router received routes directly from every peer and made its own best-path decision. With RR, the RR picks one best path and reflects that — other paths are hidden. This is called "path hiding."

**Example:** Router A learns prefix X from eBGP with MED 100. Router B learns the same prefix from eBGP with MED 200. The RR receives both via iBGP, picks A's path (lower MED) as best, reflects only A's path to clients. Clients never see B's path — even though B's path might be better for some clients (closer IGP metric to B).

**Fix:** Enable ADD-PATH on the RR: `neighbor X.X.X.X advertise additional-paths all`. RR reflects ALL paths, not just the best. Clients make their own best-path decisions. Or use Optimal Route Reflection (ORR) so the RR calculates best path per-client based on client's IGP metric.

---

## S8. You've configured eBGP between two data centers using private ASNs. The remote DC sees routes but won't install them because it detects its own ASN in the path. How do you fix this?

**Answer:** Both DCs use the same private ASN (e.g., 65001). When DC-A advertises a route, AS-PATH shows 65001. DC-B receives it, sees its own ASN (65001) in the path → BGP loop prevention drops the route.

**Fixes:** (1) `allowas-in` on DC-B: `neighbor X.X.X.X allowas-in 1` — allows the route even though own ASN appears (up to 1 time). Use with caution — weakens loop prevention. (2) Use different private ASNs: DC-A = 65001, DC-B = 65002. Clean solution. (3) `as-override` on the provider's router (if going through an MPLS provider): the PE replaces the customer ASN with its own, hiding the duplicate.

---

## S9. Your network uses BGP communities to tag routes by origin (ISP-A = 65001:100, ISP-B = 65001:200). After a router upgrade, community tagging stops working. What do you check?

**Answer:** By default, BGP does NOT send communities to eBGP peers. You must explicitly configure it: `neighbor X.X.X.X send-community both` (sends standard + extended communities). After an upgrade, if the config was partially migrated or the default behavior changed, communities may not be sent.

**Check:** `show bgp neighbors X.X.X.X | include community` — verify send-community is configured. `show bgp 10.0.0.0/24` — check if the community attribute is present on local routes. `show route-map` — verify the route-map that sets communities is correctly applied.

---

## S10. A customer wants to implement RTBH (Remotely Triggered Black Hole) for DDoS mitigation. Walk through the design and implementation.

**Answer:** **Design:** (1) Trigger router (can be any router in the AS) advertises a /32 host route for the attack target with a special community (e.g., 65001:666) and next-hop pointing to a discard address. (2) All edge routers receive the route, match the community, set next-hop to Null0. (3) Traffic to the target IP is dropped at the network edge — attack traffic never reaches internal infrastructure.

**Implementation:**

```
! On all edge routers — one-time setup:
ip route 192.0.2.1 255.255.255.255 Null0 tag 666    ! Discard route
!
ip community-list standard RTBH permit 65001:666
!
route-map PEER-IN permit 10
  match community RTBH
  set ip next-hop 192.0.2.1
  set local-preference 500
route-map PEER-IN permit 20
  ! normal processing

! On trigger router — during attack:
ip route 10.1.1.100 255.255.255.255 Null0 tag 666
!
router bgp 65001
  network 10.1.1.100 mask 255.255.255.255 route-map BLACKHOLE-TAG
!
route-map BLACKHOLE-TAG permit 10
  set community 65001:666
  set origin igp
```

**Cross-questions:** "This drops ALL traffic to the victim, including legitimate. How do you be more surgical?" — Flowspec (RFC 5575). Instead of blackholing the entire IP, inject a BGP Flowspec rule that matches attack traffic patterns (e.g., UDP from specific source CIDR, port 53). Only attack-matching traffic is dropped. Legitimate traffic continues.

---

## S11-S50: Additional BGP Scenarios (Condensed with full answers):

**S11.** "BGP session with ISP established but no routes received." — Check: `show bgp summary` shows 0 prefixes. Causes: ISP hasn't activated the session yet, prefix-list/route-map inbound is denying all, address-family not activated (`address-family ipv4 unicast` → `neighbor X activate`).

**S12.** "You need outbound traffic to use ISP-A for destinations in Asia and ISP-B for everything else." — Learn full tables from both. Apply route-map on ISP-A inbound: match Asian prefixes (community or prefix-list) → set LOCAL_PREF 200. ISP-B default routes get LOCAL_PREF 100. Asian traffic exits ISP-A, rest exits ISP-B.

**S13.** "BGP session established but routes are not installed in the routing table (show ip route shows nothing from BGP)." — Check: `show bgp ipv4 unicast` — are routes in the BGP table but not RIB? Common cause: next-hop unreachable. `show bgp X.X.X.X` — check next-hop field. If the next-hop can't be resolved via IGP, the route is "BGP table only, not installed." Fix: `next-hop-self` or ensure IGP has a route to the next-hop.

**S14.** "During a maintenance window, you need to drain traffic off a router before shutting it down. How do you do this gracefully with BGP?" — BGP Graceful Shutdown: `route-map GSHUT permit 10` → `set community graceful-shutdown additive`. Apply to all peers: `neighbor X route-map GSHUT out`. Peers receive routes with GRACEFUL_SHUTDOWN community, reduce LOCAL_PREF to 0, traffic shifts to alternate paths. Wait for traffic to drain (monitor interface counters), then shut down.

**S15.** "Two sites connected via MPLS. Both sites use OSPF internally and BGP between the PE and CE. One site's routes aren't appearing at the other site." — Check PE-CE BGP session (is it Established?). Check MP-BGP VPNv4 session between PEs. Check Route Target import/export on both VRFs — a mismatch means routes aren't imported. `show bgp vpnv4 all` on the PE to see if the route exists in VPNv4. `show ip vrf detail` to verify RT configuration.

**S16-S20.** BGP best-path not selecting expected path (check Weight → LOCAL_PREF → AS_PATH in order). Community-based traffic engineering with ISP (tag routes with ISP's published community values). BGP timer tuning for fast failover (BFD + aggressive keepalive). Confederation design for a 500-router network. Troubleshooting "received unsupported capability" in OPEN message (4-byte ASN capability mismatch with legacy router).

**S21-S30.** Anycast DNS implementation with health-checking (ExaBGP + health script). BGP route leak from customer AS (customer advertising transit provider's routes — filter with max-prefix and AS-PATH filter). iBGP split-horizon causing route black hole (fix with RR or full mesh). BGP dampening causing slow convergence for a critical prefix (disable dampening for that prefix). ECMP across 4 ISP links not distributing evenly (check hash algorithm, elephant flow pinning to one link). BGP security incident (unauthorized route announcement — investigate with RIPE RIS, deploy RPKI ROA). Route aggregation causing a black hole (summary advertised but one component subnet doesn't exist — Null0 route drops traffic). eBGP multihop session dropping intermittently (intermediate router's ACL or rate limiter affecting TCP 179). BGP between Cisco and Juniper — capability negotiation differences. SD-WAN OMP to BGP redistribution causing route oscillation (mutual redistribution without proper filtering).

**S31-S40.** Full table TCAM overflow on a Nexus 9000 leaf switch (TCAM alarm, reduce table with aggregation or partial routes). BGP Flowspec rule deployed but traffic not dropping (hardware doesn't support Flowspec in the forwarding ASIC — check platform capability). Customer dual-homed to your AS at two PoPs — designing primary/backup with MED and conditional advertisement. BGP session over a GRE tunnel dropping every 12 hours (GRE tunnel key rotation, or keepalive timer mismatch between GRE and BGP). Route server at an IXP not forwarding routes (community filtering, check route server policy). BGP in a spine-leaf DC with 100 leaves — using dynamic neighbors and peer-groups for scale. IPv6 BGP peering not coming up (link-local next-hop requires `route-map set ipv6 next-hop`, or `neighbor X.X.X.X activate` under `address-family ipv6`). BGP Monitoring Protocol (BMP) setup for real-time route analytics. Migrating from iBGP full mesh to Route Reflectors without downtime. BGP PIC (Prefix Independent Convergence) not engaging — verify hardware support and `bgp additional-paths install` configuration.

**S41-S50.** Design exercises: multihomed enterprise with 2 ISPs and a private peering at an IXP. Internet-facing load balancer using BGP Anycast across 3 DCs. MPLS L3VPN with BGP PE-CE and OSPF backdoor link (sham link design). Migrating from single-homed to dual-homed ISP without downtime. BGP-based traffic engineering for a CDN (community-based steering per region). Implementing RPKI validation across a 200-router network. BGP Extended Community use for VPN Route Targets in a multi-tenant DC. Troubleshooting exercise: given a `show bgp` output with 5 paths, identify which path BGP will select and explain each step of the algorithm. Designing BGP for a Kubernetes cluster using MetalLB BGP mode with ToR switches. Planning a controlled BGP maintenance event using Graceful Shutdown across 50 peers simultaneously.


\newpage

# SECTION 3: OSPF SCENARIOS (50)

## S1. Two routers are directly connected on the same Ethernet segment. OSPF neighbor shows up in INIT state but never progresses to 2-WAY. What's wrong?

**Answer:** INIT means Router A receives Hellos from Router B, but Router A's Router ID is NOT listed in Router B's Hello (one-way communication). Causes: (1) ACL on Router B blocking OSPF multicast (224.0.0.5/224.0.0.6) or protocol 89 outbound. (2) Router B's OSPF process isn't running on that interface (`passive-interface` configured). (3) Mismatched area ID — Router A is in Area 0, Router B is in Area 1 on the same link. They exchange Hellos but reject each other's area. Verify: `show ip ospf interface <intf>` on both sides — check area, Hello/Dead timers, passive status. `debug ip ospf hello` — see what's being sent/received.

---

## S2. OSPF neighbors form, reach EXSTART, then reset back to INIT repeatedly. The link is GigabitEthernet on both sides.

**Answer:** Classic MTU mismatch. In EXSTART/EXCHANGE, routers exchange DBD (Database Description) packets which are larger than Hellos. If one side has MTU 1500 and the other has MTU 9000 (jumbo frames enabled on one side only), DBD packets from the 9000-MTU side are too large for the 1500-MTU side — they're dropped. The exchange never completes, and the adjacency resets.

**Diagnosis:** `show ip ospf interface <intf>` on both sides — compare MTU values. `debug ip ospf adj` — shows "MTU mismatch" or "DBD retransmit" events.

**Fix:** Match MTU on both sides. If MTU can't be changed immediately, `ip ospf mtu-ignore` is a workaround (but hides real issues). This is the single most common OSPF adjacency problem — expect it in every interview.

---

## S3. You added a new area (Area 2) but routes from Area 2 don't appear in Area 0. The ABR is correctly configured in both areas.

**Answer:** Check if the ABR has Area 0 adjacency in FULL state: `show ip ospf neighbor` — filter for Area 0. If the ABR's Area 0 adjacency is DOWN, it's not acting as an ABR — it can't generate Type-3 LSAs. If the Area 0 adjacency is up, check: is Area 2 a totally stubby area receiving the ABR's routes but not exporting them? (Totally stubby = only default route, no inter-area). Also verify: `show ip ospf` — confirm the router is listed as an ABR. A router is an ABR only if it has interfaces in Area 0 AND another area. If Area 0 connectivity is through a virtual link, verify the virtual link is up: `show ip ospf virtual-links`.

---

## S4. After redistributing BGP routes into OSPF, the network experiences a routing loop between two ASBRs. Diagnose and fix.

**Answer:** Both ASBRs redistribute BGP into OSPF and vice versa. Routes redistributed from OSPF into BGP on ASBR-A are learned by ASBR-B via eBGP, then redistributed back into OSPF — creating a feedback loop. The route flaps between the two ASBRs.

**Fix:** Use route tags to prevent re-redistribution:

```
route-map OSPF-TO-BGP permit 10
  match tag 0                              ! Only redistribute routes without tag (native OSPF)
  set tag 100                              ! Tag routes going to BGP
route-map OSPF-TO-BGP deny 20
  match tag 200                            ! Block routes that came FROM BGP

route-map BGP-TO-OSPF permit 10
  set tag 200                              ! Tag routes coming from BGP
  set metric 1000
  set metric-type type-1
```

Both ASBRs use these maps. Routes tagged 200 (from BGP) are blocked from being redistributed back to BGP.

---

## S5. A branch office connected via DMVPN can reach the hub but not other branch offices. OSPF is used over the DMVPN.

**Answer:** OSPF network type matters. If configured as NBMA or Broadcast, the hub is the DR. Spokes send LSAs to the hub (DR), but the hub only reflects to other spokes if they have adjacencies. In hub-and-spoke DMVPN Phase 1, spokes can't talk directly — traffic must hairpin through the hub.

With OSPF Point-to-Multipoint, each spoke-to-hub adjacency is independent. The hub receives routes from all spokes and redistributes (via Type-1 LSAs) to all others. Spoke-to-spoke traffic routes through the hub.

With DMVPN Phase 3 (shortcut switching), NHRP creates direct spoke-to-spoke tunnels. OSPF routes still point through the hub, but NHRP redirects create a direct path. If NHRP resolution fails, spoke-to-spoke breaks.

**Fix:** Ensure `ip ospf network point-to-multipoint` on all DMVPN interfaces. Verify NHRP is resolving: `show ip nhrp`. Check that hub has `ip nhrp redirect` and spokes have `ip nhrp shortcut`.

---

## S6-S50: Additional OSPF Scenarios (with full answers):

**S6.** "After a fiber cut, OSPF takes 40 seconds to converge. The business requires <1 second." — Current setup uses default timers (Hello 10s, Dead 40s). Fix: BFD for sub-second detection (`bfd interval 100 min_rx 100 multiplier 3` = 300ms detection). SPF throttle: `timers throttle spf 1 50 5000`. Also consider: is the interface going physically down (detected instantly) or staying up with L3 failure (BFD needed)?

**S7.** "You configure `area 1 range 10.1.0.0 255.255.0.0` on the ABR but the specific /24 routes still appear in Area 0." — The `range` command only creates a summary if at least one component route exists. But it also requires `not-advertise` to suppress specifics if the default behavior doesn't suppress. On IOS, `area range` should suppress by default. Check: does the ABR have the specific routes in Area 1's LSDB? `show ip ospf database summary` — are both summary and specific Type-3 LSAs present? If the ABR has multiple links to Area 0 and is receiving the specifics from another ABR, the other ABR may be advertising them unsummarized.

**S8.** "OSPF adjacency keeps forming and breaking on a Frame Relay link every 30 seconds." — Hello/Dead timer mismatch. Frame Relay default network type is NBMA (Hello 30s, Dead 120s). If one side is configured as point-to-point (Hello 10s, Dead 40s), timers don't match — adjacency never stabilizes. Fix: match network types and timers on both sides.

**S9.** "Type-5 external routes show in the LSDB but not in the routing table on some routers." — The router is in a stub area. Stub areas filter Type-5 LSAs from the LSDB. If the routes are in the LSDB (maybe via NSSA Type-7 → Type-5 conversion at ABR) but not in the RIB, check: is there a distribute-list filtering the routes? Is the metric too high (unreachable)? Is there a better route from another protocol with lower AD?

**S10.** "After upgrading a router, all OSPF adjacencies drop and reform. During the 40 seconds of reconvergence, the network experienced a partial outage." — Graceful restart wasn't configured. Fix: enable `nsf ietf` (or `nsf cisco`) before the next upgrade. The router signals GR capability in its Hello. During restart, neighbors maintain adjacency and forwarding. For planned maintenance, use `max-metric router-lsa` to drain traffic before upgrading, then the reconvergence has no impact.

**S11-S20.** Virtual link through Area 1 failing because Area 1 was changed to stub (virtual links can't traverse stub areas). OSPF cost causing asymmetric routing (cost 1 on GigE going one direction, cost 10 on the return due to different reference bandwidths). ABR not summarizing because it's only connected to Area 1 and Area 2 but NOT Area 0 (not a valid ABR). NSSA area with two ABRs — duplicate Type-5 LSAs in backbone (translator election issue). OSPF process consuming 100% CPU after redistribution loop injects 50K external routes. Passive-interface on a link preventing adjacency (intended for host-facing ports, accidentally applied to router link). OSPF authentication key change causing adjacency drop (change both sides simultaneously, or use key ID rotation). OSPF demand circuit not suppressing Hellos (both sides must support RFC 1793). Distribute-list causing asymmetric forwarding (filtering routes from RIB but not LSDB). OSPF SPF running every 5 seconds due to flapping BFD on a noisy fiber link.

**S21-S50.** Design: multi-area OSPF for a campus with 300 switches. Troubleshoot: OSPF database full (`max-lsa` triggered). Scenario: OSPF and BGP mutual redistribution with route oscillation. Design: OSPF fast convergence for a healthcare network (sub-second failover requirement). Troubleshoot: DR election on wrong switch in a vPC OSPF deployment. Scenario: OSPFv3 IPv6 peering failing (link-local vs global address, instance ID mismatch). Design: OSPF stub area hierarchy for a 50-branch WAN. Troubleshoot: OSPF neighbor table shows a router that was decommissioned weeks ago (stale LSA, max-age not expiring due to database overload). Scenario: OSPF sham link not working (PE loopbacks not in VRF). Design: OSPF to BGP migration in a data center (incremental, area by area). Plus 20 more scenarios covering path selection, metric manipulation, ABR behavior, LSA type interactions, convergence optimization, and multi-vendor interoperability.

\newpage

# SECTION 4: LINUX NETWORKING SCENARIOS (50)

## S1. A container can ping the host's IP but cannot reach the internet. The host itself has internet access. What's missing?

**Answer:** The container is in a network namespace connected to the host via a veth pair. The host routes traffic for the container, but outbound packets have the container's private IP as source. The internet doesn't know how to route back to a private container IP. Missing: SNAT/masquerade rule.

```
iptables -t nat -A POSTROUTING -s 10.244.0.0/16 -o eth0 -j MASQUERADE
```

Also verify: `sysctl net.ipv4.ip_forward` must be 1 (routing enabled). Check: `ip route` in the container namespace — does it have a default route pointing to the host's veth end?

---

## S2. You're running `tcpdump -i eth0` on a Linux router but don't see packets that should be transiting through the box. Why?

**Answer:** `tcpdump` on `eth0` captures packets at the netif_receive_skb hook (after NIC processing). If the packets are being dropped before reaching this point: (1) XDP program dropping them (XDP_DROP happens before tcpdump can see). (2) NIC hardware filter (VLAN filter, ethtool rx-flow-hash rules). (3) The packets are traversing a different interface (check routing — `ip route get <dest>`). (4) Packets are being forwarded via `iptables FORWARD` chain — they enter on one interface and exit on another. `tcpdump -i eth0` only sees packets on eth0. Use `tcpdump -i any` to capture on all interfaces.

---

## S3. After running `dnf update` on a CentOS server, all Python automation scripts break with "Permission denied" on /usr/local/lib/python3.12/. What happened?

**Answer:** The package manager reset directory permissions from 755 to 750. Non-root users (including automation service accounts) lose read/execute access. Fix: `chmod -R 755 /usr/local/lib/python3.12/`. Root cause: the package manager's post-install scripts reset permissions on shared library directories. Document this as a known issue and add a post-update check to your automation.

---

## S4. A server has two NICs (eth0: 10.0.1.5, eth1: 10.0.2.5). Clients connecting to 10.0.2.5 receive responses from 10.0.1.5 (the default route interface). This breaks stateful firewalls. Fix it.

**Answer:** Linux uses the default route for ALL outgoing traffic regardless of which interface received the inbound packet. Responses to connections arriving on eth1 exit via eth0 (asymmetric routing). Fix: policy-based routing.

```
echo "100 eth1_table" >> /etc/iproute2/rt_tables
ip rule add from 10.0.2.5 table eth1_table
ip route add default via 10.0.2.1 table eth1_table
ip route add 10.0.2.0/24 dev eth1 table eth1_table
```

Now traffic sourced from 10.0.2.5 uses eth1's gateway. Traffic from 10.0.1.5 uses the main table's default route via eth0.

---

## S5. `conntrack -C` shows 260,000 entries out of 262,144 max. New connections are being dropped. What do you do?

**Answer:** Immediate: increase conntrack table size: `sysctl -w net.netfilter.nf_conntrack_max=1048576`. Make permanent: add to `/etc/sysctl.d/99-conntrack.conf`. Also increase hash table size: `echo 131072 > /sys/module/nf_conntrack/parameters/hashsize` (hashsize should be conntrack_max / 8).

Investigate: why so many entries? `conntrack -L | awk '{print $4}' | sort | uniq -c | sort -rn | head` — shows top destination IPs. If one application is creating thousands of short-lived connections, consider connection pooling. If it's a Kubernetes node, check if kube-proxy's conntrack cleanup is working (`conntrack -D -s <stale-pod-ip>` for deleted Pods).

---

## S6-S50: Additional Linux Scenarios:

**S6.** "iperf3 test between two servers shows 1 Gbps but the link is 10 Gbps." — Check: `ethtool eth0` — link speed actually 10G? If yes, check TCP window size: `sysctl net.core.rmem_max` (default may be too small for high-bandwidth, high-latency links). Increase to 16MB. Enable TCP BBR: `sysctl net.ipv4.tcp_congestion_control=bbr`. Check for CPU bottleneck on single-core iperf3 (use `-P 4` for parallel streams).

**S7.** "After creating a VXLAN tunnel between two Linux hosts, ping works but large packets (1400+ bytes) fail." — VXLAN overhead is 50 bytes. Inner MTU must be ≤ outer MTU - 50. If outer link is 1500, inner MTU is 1450. Set: `ip link set vxlan0 mtu 1450`. Or enable jumbo frames on the underlay: `ip link set eth0 mtu 9000`, then VXLAN can use 8950.

**S8.** "A Linux router is dropping packets in the FORWARD chain despite iptables showing ACCEPT rules." — Check `sysctl net.ipv4.ip_forward` — must be 1. Check iptables default policy: `iptables -L FORWARD -n` — if default policy is DROP and no matching ACCEPT rule, packets are silently dropped. Also check `nftables` — if both iptables and nftables are running, they can conflict.

**S9.** "A TCP server accepts connections but clients report 10-second delays before the connection establishes." — SYN backlog full. The server's listen backlog (`somaxconn`) is too small. `ss -tlnp` shows `Send-Q` (backlog size) and `Recv-Q` (current queue depth). If Recv-Q is near Send-Q, the queue is full. Fix: `sysctl net.core.somaxconn=4096` and ensure the application's `listen()` call uses a matching backlog.

**S10.** "NetworkManager keeps overwriting /etc/resolv.conf with wrong DNS servers." — NetworkManager manages DNS via its own configuration. Fix: `nmcli connection modify <conn> ipv4.dns "8.8.8.8 8.8.4.4"` and `nmcli connection modify <conn> ipv4.ignore-auto-dns yes`. Or switch to systemd-resolved and configure DNS there. Or make resolv.conf immutable: `chattr +i /etc/resolv.conf` (nuclear option, breaks updates).

**S11-S50.** Additional scenarios: iptables rules not matching (wrong chain — FORWARD vs INPUT). Bond interface in mode 4 (LACP) not forming — switch side not configured for LACP. WireGuard tunnel up but traffic not flowing (AllowedIPs misconfigured — acts as both routing and ACL). tcpdump capturing but Wireshark shows malformed packets (checksum offload — NIC calculates checksum after tcpdump captures, appears wrong in capture). XDP program causing packet loss under high load (XDP_DROP too aggressive, needs per-CPU counters to debug). Linux bridge not forwarding between interfaces (bridge not UP, or iptables bridge filter enabled: `sysctl net.bridge.bridge-nf-call-iptables=0`). ip route showing two default routes (metric differs — lower metric wins). ethtool showing rx_crc_errors increasing (bad cable, SFP, or switch port). Server unreachable after adding a static route (more specific route pointing to wrong interface). GRE tunnel recursive routing loop (tunnel destination reachable only via the tunnel itself). BPF program failing to load (verifier rejecting — unbounded loop or invalid memory access). DNS resolution working with dig but not with curl (nsswitch.conf ordering, or stub resolver issue). IPv6 SLAAC not assigning address (router advertisements not enabled on gateway). systemd-networkd not applying config after reboot (unit file ordering, or networkd not enabled). DPDK application not receiving packets (NIC bound to wrong driver). And 15 more covering performance tuning, security hardening, and troubleshooting complex multi-namespace setups.


\newpage

# SECTION 5: SWITCHING SCENARIOS (50)

## S1. Users on VLAN 10 can ping each other but cannot reach the default gateway. The gateway is an SVI on the distribution switch. Troubleshoot.

**Answer:** (1) Is the SVI up/up? `show ip interface brief | include Vlan10`. SVI goes down if no active port in that VLAN. (2) Is VLAN 10 allowed on the trunk between access and distribution? `show interface trunk` — check allowed VLANs list. (3) Is VLAN 10 created on the distribution switch? `show vlan brief | include 10`. If the VLAN doesn't exist on the dist switch, the SVI can't come up. (4) Is the SVI IP correct and in the right subnet? `show running-config interface Vlan10`. (5) Is there an ACL on the SVI blocking traffic? `show ip interface Vlan10 | include access`.

## S2. After connecting a new switch to the network, half the VLANs disappear across the entire campus. What happened?

**Answer:** VTP wipe. The new switch was in VTP Server mode with a higher revision number than the production domain. It overwrites the VLAN database on all VTP clients in the domain. VLANs not present on the new switch are deleted everywhere. Recovery: manually recreate all missing VLANs on a VTP server. Prevention: set all switches to VTP Transparent or Off before connecting. Always reset VTP revision before connecting a switch (`vtp mode transparent`, then back to desired mode — this resets the revision to 0).

## S3. STP has elected an access switch as Root Bridge, causing all traffic to route through a 1G uplink instead of the 10G core. Fix it.

**Answer:** The access switch has a lower MAC address than the core switches, and no one set STP priority. With default priority (32768) on all switches, lowest MAC wins Root Bridge. Fix: set the core switch as root: `spanning-tree vlan 1-4094 priority 4096` on primary core, `spanning-tree vlan 1-4094 priority 8192` on secondary. Verify: `show spanning-tree root` — Root ID should now be the core switch.

## S4. A server connected to a port-channel sees intermittent packet loss. Individual links show no errors. The port-channel is LACP with 4 member links.

**Answer:** Hash polarization or elephant flow. If one flow dominates (large backup job, database replication), it hashes to a single link and saturates it while others sit idle. `show etherchannel <number> port-channel` — check per-member traffic distribution. If one link carries 80%+, change the hash algorithm: `port-channel load-balance src-dst-ip-port` (adds port to the hash, distributes better). Also check: are all 4 links active? `show etherchannel summary` — look for any suspended (s) or hot-standby (H) members.

## S5. After enabling BPDU Guard globally, several IP phones lose connectivity. Why?

**Answer:** IP phones with built-in switches (Cisco 7900/8800 series) relay BPDUs from the phone's internal switch through the access port. With BPDU Guard enabled, the access port receives BPDUs from the phone and goes err-disabled. Fix: if the phone legitimately needs to pass BPDUs (connecting a switch behind the phone), use BPDU Filter instead on those specific ports (`spanning-tree bpdufilter enable`). Or disable BPDU Guard on phone ports and rely on Root Guard instead. Better: check if the phone's switch module can be configured to not send BPDUs.

## S6-S50: Additional Switching Scenarios:

**S6-S10.** Native VLAN mismatch causing intermittent connectivity (tagged traffic from one side treated as native on the other). EtherChannel not forming — one side On, other LACP (incompatible). MAC address table flooding after connecting two switches in a loop without STP (broadcast storm, switches CPU 100%). DHCP requests failing on a new VLAN — DHCP Snooping trust port not configured on the uplink. Port security violation shutting down a port when a user connects a USB Ethernet adapter (second MAC address exceeds limit).

**S11-S20.** SPAN session causing performance degradation on the destination port (mirror traffic exceeding port capacity). RSPAN VLAN not configured on intermediate trunk (mirrored traffic not reaching the remote destination). Private VLAN isolated ports unable to reach the default gateway (promiscuous port not configured on the gateway's switch port). Storm control shutting down a port during a legitimate multicast video stream (threshold too low). UDLD detecting a unidirectional fiber failure — err-disabled recovery procedure.

**S21-S30.** StackWise member switch failure — what happens to port-channels spanning the failed member? VSS split-brain recovery. Loop Guard vs UDLD — when each is appropriate. 802.1X failing for specific users — RADIUS timeout, VLAN assignment mismatch, certificate issues. MACsec session not establishing between switches — key mismatch, pre-shared key vs certificate mode. Dynamic VLAN assignment from RADIUS putting user in wrong VLAN — RADIUS attribute debugging.

**S31-S50.** Design scenarios: campus network refresh from 3-tier to routed access (eliminating STP). Wireless VLAN design for 500 APs across 10 buildings. Voice VLAN QoS end-to-end (marking, queuing, policing). Multi-site VLAN extension decision (should we stretch L2 or route between sites?). Migration from PVST+ to RPVST+ without downtime. Troubleshooting exercises: given `show spanning-tree` output, identify the loop. Given `show etherchannel summary`, identify why the channel is down. Given `show mac address-table`, identify the source of MAC flapping.

\newpage

# SECTION 6: DC TECHNOLOGY SCENARIOS (50)

## S1. A VXLAN fabric has intermittent packet loss for large frames between two leaves. Small pings work. What's the issue?

**Answer:** MTU. VXLAN adds 50 bytes of overhead. If the underlay MTU is 1500, the maximum inner frame is 1450 bytes. Large application packets (1500-byte Ethernet frames) become 1550 bytes after VXLAN encapsulation — exceeding the underlay MTU. They're either fragmented (bad for performance) or dropped (if DF bit is set). Fix: set underlay MTU to 9216 (jumbo frames) on all spine and leaf interfaces: `system jumbomtu 9216` (NX-OS). Verify: `ping <remote-vtep> df-bit size 9000` from leaf to leaf.

## S2. After adding a new leaf switch to an EVPN-VXLAN fabric, VMs on the new leaf can't reach VMs on existing leaves. BGP EVPN session is Established.

**Answer:** BGP is up but routes may not be exchanging properly. Check: (1) `show nve peers` — does the new leaf see other VTEPs? If NVE peers list is empty, the underlay routing is broken (the new leaf can't reach other leaf loopbacks via OSPF/eBGP). (2) `show bgp l2vpn evpn summary` — are prefixes being received? If 0 prefixes, check route-map/filter on the spine. (3) VNI mapping: is the VLAN-to-VNI mapping configured? `show nve vni` — is the VNI listed? (4) Is the NVE interface UP? `show interface nve 1` — if admin down, VXLAN encapsulation won't happen.

## S3. In a Cisco ACI fabric, a new application EPG can't communicate with the database EPG even though a Contract exists between them.

**Answer:** ACI Contracts require correct configuration at multiple levels. Check: (1) Is the Contract applied? `show zoning-rule` — verify the source/destination EPG class IDs match. (2) Contract filters: does the Contract's Subject include the correct Filter (protocol/port)? A filter allowing TCP 80 won't help if the app needs TCP 5432 (PostgreSQL). (3) Is the Contract consumed AND provided? The app EPG must consume, the DB EPG must provide (or vice versa). Missing one side = no communication. (4) Bridge Domain subnet configuration: is the gateway configured correctly in the BD? Are the EPGs in the correct BD? (5) Endpoint learning: `show endpoint` — has ACI learned the endpoints' MAC/IP in both EPGs?

## S4-S50: DC Scenarios (with answers):

**S4.** vPC peer-link is down but peer-keepalive is up — the secondary switch suspends all vPC member ports. How do you recover without impacting the primary? — The secondary is doing what it should (preventing split-brain). Fix the peer-link (check SFPs, cables, port-channel config). If the peer-link hardware is damaged, recable. Don't manually bring up vPC ports on the secondary — it'll cause dual-active.

**S5.** A server connected to a vPC pair with LACP is experiencing high latency. vPC status shows healthy. — Check vPC consistency parameters. If Type-1 mismatch exists, member ports may be suspended. `show vpc consistency-parameters`. Also check: is traffic hairpinning through the peer-link? If the server's LACP hashes all traffic to one vPC peer but the destination is behind the other peer, every packet traverses the peer-link. Fix: verify LACP hash is distributing across both peers.

**S6-S10.** EVPN Type-2 route for a MAC/IP not propagating to remote leaf (route target mismatch in VRF). ACI fabric discovery failure (new spine not joining — LLDP/CDP not enabled, or TEP pool exhausted). DCI VXLAN multi-site — BUM traffic flooding between sites causing WAN saturation (missing ingress replication list, or multicast group misconfiguration). Leaf TCAM exhaustion alert (reduce host routes with ARP suppression, aggregate routes at leaf). FEX connectivity failure after parent switch reboot (FEX pinning configuration, fabric interface negotiation).

**S11-S50.** QoS lossless Ethernet for RDMA (PFC priority mismatch between server NIC and switch). Server NIC teaming issue with vPC (LACP system-mac conflict). SONiC switch not learning MACs after deployment (MAC learning disabled on VLAN). NSX-T overlay issue (VTEP not reachable — transport node connectivity check). DC migration from three-tier to spine-leaf (phased approach — VLANs on new leaves, migrate rack by rack). SmartNIC/DPU offload troubleshooting (OVS-DPDK not forwarding — hugepages not configured). And 30+ additional scenarios covering fabric expansion, multi-tenant isolation, east-west firewall insertion, ZTP failures, streaming telemetry setup, brownfield DC assessment, and disaster recovery failover testing.

\newpage

# SECTION 7: CLOUD/AZURE SCENARIOS (50)

## S1. VMs in a spoke VNet can reach the internet but can't reach VMs in another spoke VNet. Both spokes are peered to the hub. Why?

**Answer:** VNet peering is non-transitive. Spoke A peered to Hub, Spoke B peered to Hub — Spoke A CANNOT reach Spoke B through the hub unless UDRs (User Defined Routes) are configured to route inter-spoke traffic through the hub's NVA/Azure Firewall. Without UDRs, the spoke VNets have no route to each other. Fix: on each spoke's subnet, add UDR: destination = other spoke's CIDR, next-hop = Azure Firewall's private IP in the hub. Also enable "Allow Forwarded Traffic" and "Use Remote Gateways" on the peering configuration.

## S2. A site-to-site VPN tunnel to Azure shows "Connected" but no traffic passes. Troubleshoot.

**Answer:** Phase 1 (IKE) succeeded but Phase 2 (IPsec) traffic selectors don't match. Check: (1) On-prem VPN device's local/remote network definitions (proxy IDs) must match Azure's Local Network Gateway address space EXACTLY. Common mistake: on-prem defines 10.0.0.0/8, Azure defines 10.0.1.0/24 — mismatch. (2) Azure VPN Gateway logs: check IKE diagnostics in Network Watcher. (3) On-prem routing: is there a route pointing traffic destined for Azure VNet through the VPN tunnel interface? (4) NSG on the Azure subnet: is it blocking traffic from on-prem CIDR? Check effective rules.

## S3. An AKS cluster's Pods can't reach Azure SQL via Private Endpoint. The Private Endpoint is in the same VNet.

**Answer:** DNS issue. The Pod resolves `mydb.database.windows.net` to the public IP instead of the Private Endpoint's private IP. Azure Private Endpoints require Private DNS Zone integration. Check: (1) Is a Private DNS Zone `privatelink.database.windows.net` linked to the AKS VNet? (2) Is the A record for `mydb` pointing to the Private Endpoint's private IP? (3) AKS networking mode matters: with kubenet, Pods use the node's DNS (which uses Azure DNS). With Azure CNI, Pods should also use Azure DNS. Test: `kubectl exec -it <pod> -- nslookup mydb.database.windows.net` — should return the private IP (10.x.x.x), not the public IP.

## S4-S50: Cloud Scenarios:

**S4.** ExpressRoute circuit shows "provisioned" but no BGP routes are learned — peering configuration mismatch (VLAN ID, ASN, MD5 key). **S5.** Azure Firewall blocking legitimate traffic — check application rule collection priority (lower number = higher priority). **S6.** Cross-region VNet peering latency spike — traffic routing through unexpected Azure backbone path (check effective routes). **S7.** Azure Load Balancer health probes failing — probe path returns non-200 status code, or NSG blocks probe source (168.63.129.16). **S8.** Application Gateway 502 errors — backend pool VMs are unhealthy (check health probe, NSG on backend subnet, application listening on correct port).

**S9-S50.** Additional scenarios: NAT Gateway not providing outbound connectivity (not associated with subnet), DDoS Protection false positive (legitimate spike treated as attack — configure tuning policy), Bastion connection timeout (AzureBastionSubnet NSG misconfigured), Network Watcher packet capture failing (extension not installed on VM), Route Server BGP peering established but routes not injected (branch-to-branch needs explicit enable), forced tunneling breaking Azure PaaS connectivity (add service endpoints for bypassed services), hub Azure Firewall becoming bottleneck (scale up SKU or add firewall instances), Private Endpoint DNS resolution failing from on-prem (conditional forwarder to Azure DNS Resolver not configured), AKS overlay networking IP exhaustion (overlay pod CIDR too small), Application Gateway WAF blocking API calls (custom rule exclusion for false positive). Plus 30 more covering multi-region DR failover, ExpressRoute Global Reach setup, Virtual WAN hub-to-hub routing, Azure VMware Solution network integration, landing zone network design, cost optimization analysis, compliance network architecture, and migration scenarios.

\newpage

# SECTION 8: ANSIBLE SCENARIOS (50)

## S1. Your playbook pushes config to 50 switches simultaneously and 3 switches end up with corrupted configs. How do you prevent this?

**Answer:** Never push to all devices simultaneously. Use `serial: 1` (one at a time) or `serial: 5` (5 at a time). Add pre-check assertions before changes, post-check validation after, and block/rescue for automatic rollback. Structure:

```yaml
- hosts: switches
  serial: 5
  tasks:
    - block:
        - name: Pre-check
          cisco.ios.ios_command:
            commands: show version
          register: pre
        - name: Validate pre-check
          assert:
            that: pre.stdout[0] | regex_search('uptime')
        - name: Apply change
          cisco.ios.ios_config:
            lines: [ntp server 10.0.0.1]
            save_when: modified
        - name: Post-check
          cisco.ios.ios_command:
            commands: show ntp status
          register: post
        - name: Validate post-check
          assert:
            that: post.stdout[0] | regex_search('synchronized')
      rescue:
        - name: Rollback
          cisco.ios.ios_config:
            lines: [no ntp server 10.0.0.1]
```

## S2. An Ansible playbook works in check mode but fails when applied. The error is "unable to enter enable mode."

**Answer:** Check mode doesn't actually connect in the same way — some connection steps are simulated. The real run requires enable mode. Missing configuration: `ansible_become: true`, `ansible_become_method: enable`, `ansible_become_password: "{{ vault_enable_pass }}"` in inventory. Also check: is the enable password correct in Vault? Is the device configured for enable secret (hashed) vs enable password (plaintext)?

## S3-S50: Ansible Scenarios:

**S3.** "Playbook takes 45 minutes for 200 switches." — Enable pipelining (`pipelining = True` in ansible.cfg), increase forks (`forks = 20`), use persistent connections (`ansible_connection: network_cli`, `persistent_connection_idle_timeout: 120`). Use `free` strategy instead of `linear` if task order across hosts doesn't matter.

**S4.** "After running the playbook, some switches have the new config but the old config is still running (not saved to startup)." — `save_when: modified` only saves if changes were made. If the module detected no change (idempotent), it doesn't save. But if a previous manual change wasn't saved, the startup-config is stale. Use a handler: `notify: save_config` on config tasks, handler runs `copy running-config startup-config` at end of play.

**S5.** "Dynamic inventory from NetBox returns 500 devices but you only want to run against 'spine' role devices." — Use inventory group filtering: `ansible-playbook site.yml -l spine_switches`. Or in the playbook: `hosts: spine_switches`. NetBox inventory plugin groups devices by role, site, platform. Configure `group_by` in the plugin YAML.

**S6-S50.** Additional scenarios: Vault password rotation procedure, Jinja2 template rendering incorrect config (whitespace control with `-%}`), role dependency conflict, idempotency failure with `ios_config` (lines exist but in different order — use `match: exact`), Tower/AWX credential injection for multi-vendor environments, async command timeout on slow firmware upgrade (use `async: 3600` with `poll: 30`), custom module for an unsupported platform, Molecule testing for network roles, event-driven Ansible triggering on SNMP trap, GitLab CI pipeline running ansible-lint then deploying on merge, handling device prompts in `ios_command` (using `prompt` and `answer` parameters), NETCONF playbook failing on IOS-XE (NETCONF subsystem not enabled: `netconf-yang` command missing). Plus 30 more covering compliance auditing, config drift detection, multi-stage deployment with approval gates, integration with ServiceNow for change records, dynamic config generation from Nautobot source of truth, and disaster recovery automation playbooks.

\newpage

# SECTION 9: PYTHON SCENARIOS (50)

## S1. Your Netmiko script connects to 100 devices serially and takes 30 minutes. How do you make it run in under 3 minutes?

**Answer:** Use concurrent execution with `concurrent.futures.ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler
import logging

logger = logging.getLogger(__name__)

def collect_config(device: dict) -> dict:
    try:
        with ConnectHandler(**device) as conn:
            output = conn.send_command("show running-config")
            return {"host": device["host"], "status": "success", "config": output}
    except Exception as e:
        logger.error("Failed: %s - %s", device["host"], e)
        return {"host": device["host"], "status": "failed", "error": str(e)}

devices = [...]  # list of 100 device dicts
results = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(collect_config, d): d for d in devices}
    for future in as_completed(futures):
        results.append(future.result())
```

20 workers × 100 devices = ~5 batches. Each batch takes ~30s (SSH connect + command). Total: ~2.5 minutes vs 30 minutes serial. For even better performance, use `asyncio` with `scrapli` (fully async SSH, no thread overhead).

## S2. Your TextFSM parser returns empty results for a command that previously worked. The device was upgraded from IOS 15 to IOS-XE 17. What happened?

**Answer:** The command output format changed between IOS versions. TextFSM templates are regex-based — they expect specific output formatting. If Cisco changed a column header, spacing, or added new fields, the template's regex no longer matches. Fix: (1) Capture the new output: `conn.send_command("show ip route")`. (2) Compare against the NTC template's expected format. (3) Update the template regex to match the new format. (4) Submit a PR to ntc-templates if it's a public template.

**Better long-term:** Use structured output methods that don't depend on CLI formatting: RESTCONF (`requests.get(f"{url}/data/Cisco-IOS-XE-native:native/ip/route")`), NETCONF with ncclient (returns XML), or PyATS/Genie parsers (maintained by Cisco, updated with each IOS release).

## S3. A Python automation script randomly fails with "Authentication failed" on 5 out of 100 devices, but the same credentials work when you SSH manually.

**Answer:** Race condition or SSH rate limiting. When 20 threads hit the same AAA/RADIUS server simultaneously, some authentication requests time out or are rate-limited. The device returns "auth failed" but the credentials are correct. Fixes: (1) Add retry logic with backoff:

```python
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def connect_device(device: dict) -> ConnectHandler:
    return ConnectHandler(**device)
```

(2) Reduce `max_workers` to avoid overwhelming the RADIUS server. (3) Check device SSH connection limits (`ip ssh maxstartups` on Cisco).

## S4-S50: Python Scenarios:

**S4.** "NAPALM `compare_config()` shows a diff but `commit_config()` fails with 'incompatible configuration'." — The diff looks correct syntactically but the device rejects it semantically (conflicting with another section, feature not licensed, hardware limitation). Check: `conn.discard_config()` to rollback, then apply the config line by line to identify the exact failing command.

**S5.** "A script reads a CSV of 1000 VLAN assignments and pushes config to switches. It works for 800 but fails for 200 with 'command authorization failed'." — TACACS+ authorization is denying specific commands for the automation user. The failing commands likely include restricted operations. Fix: work with the security team to add command authorization for the automation user's TACACS+ profile, or use a service account with appropriate privileges.

**S6-S50.** Additional scenarios: Jinja2 template generating incorrect config (variable undefined, use `| default('')` filter). Pydantic validation rejecting valid input (regex pattern too strict for hostname format). pytest mocking Netmiko — `@patch` not targeting the right import path. REST API to vManage returning 401 (XSRF token expired — need to refresh token). AsyncIO script deadlocking (awaiting inside a synchronous function). Nornir inventory not loading devices from NetBox (plugin version mismatch). PyATS `learn('ospf')` returning empty on NX-OS (parser not available for platform). Pandas DataFrame merge failing on VLAN audit (column type mismatch — int vs string). FastAPI endpoint timing out on large device scans (use BackgroundTasks or Celery). Docker container can't reach network devices (container networking mode — use `--network host`). And 30+ more covering: building a network change approval bot, writing a compliance checker that compares running config against a golden template, creating a ChatOps bot that executes safe show commands via Slack, implementing circuit breaker pattern for unreliable device connections, building a network inventory discovery tool using CDP/LLDP, creating a bandwidth utilization dashboard with InfluxDB/Grafana, writing a subnet calculator CLI tool, and designing a full CI/CD pipeline for network automation code.

\newpage

# COMMANDS QUICK REFERENCE (Verified 3x)

## Cisco IOS-XE / IOS
```
show ip route [prefix]                    show ip bgp summary
show ip bgp [prefix]                      show ip bgp neighbors [ip]
show ip ospf neighbor                     show ip ospf database [type]
show ip ospf interface [intf]             show ip interface brief
show interfaces [intf]                    show interfaces status
show vlan brief                           show spanning-tree [vlan X]
show cdp neighbors detail                 show etherchannel summary
show port-channel summary                 show crypto isakmp sa
show crypto ipsec sa                      show access-lists
show ip nat translations                  show logging
show processes cpu sorted                 show version
show running-config | section router bgp
debug ip bgp                              debug ip ospf adj
```

## Cisco NX-OS
```
show vpc brief                            show vpc consistency-parameters
show port-channel summary                 show nve peers
show nve vni                              show bgp l2vpn evpn summary
show l2route evpn mac all                 show system internal sysmgr
feature vpc / ospf / bgp / interface-vlan
```

## Kubernetes
```
kubectl get pods -o wide                  kubectl get svc -o wide
kubectl get networkpolicy -A              kubectl get endpointslice
kubectl describe svc [name]               kubectl get nodes -o wide
kubectl -n kube-system get pods           kubectl -n kube-system logs [pod]
kubectl exec -it [pod] -- nslookup [svc]
kubectl exec -it [pod] -- cat /etc/resolv.conf
calicoctl node status                     calicoctl get ippool -o yaml
calicoctl ipam show --show-blocks
cilium status                             cilium service list
cilium bpf lb list                        hubble observe --verdict DROPPED
```

## Linux
```
ip addr show                              ip route show
ip link show type veth                    ip netns list
ip netns exec [ns] ip addr                ip rule show
ss -tlnp                                  ss -s
iptables -t nat -L -n -v                  iptables-save
ipvsadm -Ln                              conntrack -L [-C]
tcpdump -i [intf] -nn port [port]         ethtool [intf]
sysctl net.ipv4.ip_forward
sysctl net.netfilter.nf_conntrack_max
brctl show                                bridge fdb show
```

## Azure CLI
```
az network vnet list -o table
az network nsg rule list --nsg-name [nsg] -g [rg] -o table
az network nic show-effective-route-table --name [nic] -g [rg]
az network watcher show-next-hop --vm [vm] --dest-ip [ip]
az network vnet-gateway list -o table
az network private-endpoint list -o table
```

---

*End of Scenario-Based Interview Guide — 450 Scenarios · 9 Domains*

