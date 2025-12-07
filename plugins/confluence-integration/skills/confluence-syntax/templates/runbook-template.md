# Runbook / Troubleshooting Guide Template

Use this template when creating operational runbooks or troubleshooting guides in Confluence with proper wiki markup syntax.

## Template

```
h2. Runbook: [System/Service Name]

{status:colour=Green|title=ACTIVE} {status:colour=Blue|title=v1.0}

||Field||Value||
|*Owner*|[~owner]|
|*Last Updated*|YYYY-MM-DD|
|*Review Cycle*|Quarterly|
|*On-Call Team*|[Team Name]|

{toc:minLevel=2|maxLevel=3}

----

h2. Overview

h3. Service Description

[Brief description of the service/system this runbook covers]

h3. Architecture Diagram

!architecture-diagram.png|width=700!

h3. Key Components

||Component||Purpose||Health Check||
|Component 1|Description|{{curl localhost:8080/health}}|
|Component 2|Description|{{systemctl status service}}|
|Component 3|Description|{{redis-cli ping}}|

h3. Dependencies

* *Upstream:* [Dependency 1], [Dependency 2]
* *Downstream:* [Consumer 1], [Consumer 2]
* *External:* [External Service]

h2. Access & Credentials

{warning:title=Security Notice}
All credentials are stored in [Vault|https://vault.example.com]. Never share credentials in plaintext.
{warning}

||Resource||Access Method||
|Production servers|SSH via bastion: {{ssh bastion.example.com}}|
|Database|Via [DB Admin Tool] with SSO|
|Monitoring|[Grafana Dashboard|https://grafana.example.com/d/xxx]|
|Logs|[Kibana|https://kibana.example.com]|

h2. Common Issues & Resolution

h3. Issue 1: [Issue Title]

{panel:title=Symptoms|bgColor=#FFEBE9}
* Symptom 1
* Symptom 2
* Error message: {{Error: Connection refused}}
{panel}

h4. Diagnosis

{code:bash}
# Check service status
systemctl status my-service

# Check logs for errors
journalctl -u my-service -n 100 --no-pager | grep -i error

# Verify connectivity
curl -v http://localhost:8080/health
{code}

h4. Resolution

# Step 1: [First action]
{code:bash}
command-to-run
{code}

# Step 2: [Second action]
{code:bash}
another-command
{code}

# Step 3: Verify resolution
{code:bash}
verification-command
{code}

{tip}
If this doesn't resolve the issue, escalate to [~senior-engineer].
{tip}

h4. Root Cause

[Explanation of why this issue occurs]

h4. Prevention

[Steps to prevent this issue from recurring]

----

h3. Issue 2: [Issue Title]

{panel:title=Symptoms|bgColor=#FFEBE9}
* Symptom 1
* Symptom 2
{panel}

h4. Diagnosis

{code:bash}
# Diagnostic commands
{code}

h4. Resolution

# Step 1: [Action]
# Step 2: [Action]
# Step 3: Verify

----

h2. Maintenance Procedures

h3. Restart Service

{note}
Coordinate with [~ops-team] before restarting production services.
{note}

{code:bash}
# Graceful restart
sudo systemctl restart my-service

# Verify service is running
systemctl status my-service
curl localhost:8080/health
{code}

h3. Scale Up/Down

{code:bash}
# Scale to N instances
kubectl scale deployment my-service --replicas=N

# Verify scaling
kubectl get pods -l app=my-service
{code}

h3. Database Maintenance

{warning}
Always take a backup before database maintenance!
{warning}

{code:bash}
# Create backup
pg_dump -h $DB_HOST -U $DB_USER dbname > backup_$(date +%Y%m%d).sql

# Verify backup
ls -la backup_*.sql
{code}

h2. Monitoring & Alerts

h3. Key Metrics

||Metric||Normal Range||Alert Threshold||Dashboard||
|CPU Usage|< 70%|> 85% for 5min|[CPU Dashboard|link]|
|Memory Usage|< 80%|> 90%|[Memory Dashboard|link]|
|Request Latency|< 200ms|> 500ms p99|[Latency Dashboard|link]|
|Error Rate|< 0.1%|> 1%|[Errors Dashboard|link]|

h3. Alert Response

||Alert||Severity||Response||
|High CPU|Warning|Check for traffic spike or runaway process|
|High Memory|Warning|Check for memory leaks, consider restart|
|High Latency|Critical|Check dependencies, database, scale up|
|High Error Rate|Critical|Check logs, rollback if recent deploy|

h2. Escalation

||Level||Contact||When to Escalate||
|L1|On-call engineer|First response|
|L2|[~senior-engineer]|Issue unresolved after 30 min|
|L3|[~tech-lead]|Major outage, data loss risk|
|Management|[~engineering-manager]|Customer impact > 1 hour|

h2. Recovery Procedures

h3. Rollback Deployment

{code:bash}
# List recent deployments
kubectl rollout history deployment/my-service

# Rollback to previous version
kubectl rollout undo deployment/my-service

# Or rollback to specific revision
kubectl rollout undo deployment/my-service --to-revision=N
{code}

h3. Restore from Backup

{code:bash}
# List available backups
aws s3 ls s3://backups/database/

# Restore specific backup
pg_restore -h $DB_HOST -U $DB_USER -d dbname backup_file.sql
{code}

h2. Post-Incident

After resolving any incident:

# Update this runbook if new issues discovered
# Create ticket for root cause analysis: [PROJ project|https://jira.example.com/projects/PROJ]
# Schedule post-mortem if severity >= P2
# Update monitoring if gaps identified

----

{info:title=Feedback}
Found an issue or have improvements? Update this page or contact [~owner].
{info}
```

## Example - Filled Template

```
h2. Runbook: Payment Processing Service

{status:colour=Green|title=ACTIVE} {status:colour=Blue|title=v2.1}

||Field||Value||
|*Owner*|[~payments-lead]|
|*Last Updated*|2025-01-15|
|*Review Cycle*|Monthly|
|*On-Call Team*|Payments Team|

{toc:minLevel=2|maxLevel=3}

----

h2. Overview

h3. Service Description

The Payment Processing Service handles all payment transactions including credit card processing, refunds, and payment method management. It integrates with Stripe and PayPal as payment providers.

h3. Architecture Diagram

!payments-architecture.png|width=700!

h3. Key Components

||Component||Purpose||Health Check||
|payments-api|REST API for payment operations|{{curl payments-api:8080/health}}|
|payments-worker|Async job processing|{{curl payments-worker:8081/health}}|
|Redis|Session and cache storage|{{redis-cli -h redis ping}}|
|PostgreSQL|Transaction storage|{{pg_isready -h postgres}}|

h3. Dependencies

* *Upstream:* [Order Service], [User Service]
* *Downstream:* [Notification Service], [Analytics Service]
* *External:* [Stripe API|https://stripe.com], [PayPal API|https://paypal.com]

h2. Access & Credentials

{warning:title=Security Notice}
All credentials are stored in [Vault|https://vault.example.com/ui/vault/secrets/payments]. Never share credentials in plaintext. PCI-DSS compliance required.
{warning}

||Resource||Access Method||
|Production servers|SSH via bastion: {{ssh payments-bastion.internal}}|
|Database|Via PgAdmin with SSO + MFA|
|Stripe Dashboard|[Stripe Dashboard|https://dashboard.stripe.com] (restricted access)|
|Monitoring|[Payments Grafana|https://grafana.example.com/d/payments]|
|Logs|[Payments Kibana|https://kibana.example.com/app/discover#/?payments]|

h2. Common Issues & Resolution

h3. Issue 1: Payment Timeout Errors

{panel:title=Symptoms|bgColor=#FFEBE9}
* Customers see "Payment processing failed" error
* Logs show: {{Error: Request timeout after 30000ms}}
* Stripe webhook deliveries delayed
{panel}

h4. Diagnosis

{code:bash}
# Check service latency
curl -w "@curl-format.txt" -s payments-api:8080/health

# Check Stripe API status
curl https://status.stripe.com/api/v2/status.json | jq .status

# Check connection pool
psql -h postgres -U payments -c "SELECT count(*) FROM pg_stat_activity WHERE datname='payments';"

# Check Redis connection
redis-cli -h redis info clients
{code}

h4. Resolution

# Step 1: Check if Stripe is experiencing issues
Visit [Stripe Status|https://status.stripe.com]. If degraded, wait for resolution.

# Step 2: If Stripe is healthy, check connection pools
{code:bash}
# Restart payments-api to reset connections
kubectl rollout restart deployment/payments-api

# Monitor recovery
kubectl logs -f deployment/payments-api --tail=100
{code}

# Step 3: If issue persists, scale up
{code:bash}
kubectl scale deployment/payments-api --replicas=6
{code}

# Step 4: Verify resolution
{code:bash}
# Check error rate in Grafana
# Test payment flow in staging
curl -X POST payments-api:8080/api/v1/payments/test
{code}

{tip}
If Stripe is healthy but timeouts persist, check for database locks or slow queries.
{tip}

h4. Root Cause

Usually caused by:
* Stripe API latency during high traffic periods
* Connection pool exhaustion under load
* Database slow queries blocking transactions

h4. Prevention

* Monitor Stripe status proactively
* Auto-scaling based on queue depth
* Connection pool tuning based on load testing

----

h3. Issue 2: Failed Webhook Processing

{panel:title=Symptoms|bgColor=#FFEBE9}
* Payment status not updating after successful charge
* Stripe dashboard shows webhook delivery failures
* Logs show: {{Error: Webhook signature verification failed}}
{panel}

h4. Diagnosis

{code:bash}
# Check webhook logs
kubectl logs deployment/payments-worker | grep webhook | tail -50

# Verify webhook secret is current
vault kv get secret/payments/stripe | grep webhook

# Check Stripe webhook status
# Go to Stripe Dashboard > Developers > Webhooks
{code}

h4. Resolution

# Step 1: Verify webhook secret matches Stripe
{code:bash}
# Compare with Stripe dashboard
vault kv get secret/payments/stripe
{code}

# Step 2: If secret mismatch, update and restart
{code:bash}
vault kv put secret/payments/stripe webhook_secret="whsec_xxx"
kubectl rollout restart deployment/payments-worker
{code}

# Step 3: Replay failed webhooks in Stripe dashboard

----

h2. Escalation

||Level||Contact||When to Escalate||
|L1|On-call engineer|First response, follow runbook|
|L2|[~payments-lead]|Unresolved after 30 min, affecting > 100 users|
|L3|[~engineering-director]|Revenue impact > $10k, outage > 1 hour|
|Exec|[~cto]|Complete payment outage, media attention|

{info:title=Feedback}
Found an issue or have improvements? Update this page or contact [~payments-lead].
{info}
```

## Checklist Before Publishing

- [ ] Service name and version status in title
- [ ] Owner and last updated date
- [ ] {toc} for easy navigation
- [ ] Architecture diagram
- [ ] Key components with health checks
- [ ] Dependencies documented
- [ ] Access methods with security warnings
- [ ] Each issue has: symptoms in {panel}, diagnosis commands, resolution steps, root cause, prevention
- [ ] Maintenance procedures with commands
- [ ] Monitoring metrics and alert thresholds
- [ ] Escalation matrix with contacts
- [ ] Recovery procedures (rollback, restore)
- [ ] Post-incident checklist
