# Confluence Documentation Page Template

Use this template when creating technical documentation pages in Confluence with proper wiki markup syntax.

## Template

```
{toc:minLevel=2|maxLevel=3}

----

h2. Overview

[Provide a brief summary of what this document covers]

{info:title=Version}
This document applies to version X.X and later.
Last updated: YYYY-MM-DD
{info}

h2. Prerequisites

Before you begin, ensure you have:

* Prerequisite 1
* Prerequisite 2
* Prerequisite 3

h2. Installation

h3. Step 1: [First Step Title]

[Description of the first step]

{code:bash}
# Command or code for step 1
example-command --option value
{code}

h3. Step 2: [Second Step Title]

[Description of the second step]

{code:bash}
# Command or code for step 2
another-command
{code}

h2. Configuration

h3. Basic Configuration

||Setting||Description||Default||
|{{setting_name}}|Description of setting|{{default_value}}|
|{{another_setting}}|Another description|{{value}}|

{panel:title=Configuration Example|bgColor=#f5f5f5}
{code:yaml}
# Example configuration file
setting_name: value
another_setting: other_value
{code}
{panel}

h3. Advanced Configuration

{expand:Click to see advanced options}
Advanced configuration details here.

||Option||Description||
|{{advanced_option}}|Description|
{expand}

h2. Usage

h3. Basic Usage

[Describe basic usage patterns]

{code:bash}
# Basic usage example
command --basic-option
{code}

h3. Common Use Cases

h4. Use Case 1: [Title]

[Description and example]

h4. Use Case 2: [Title]

[Description and example]

h2. Troubleshooting

{warning:title=Common Issues}
If you encounter problems, check the following first:
* Issue 1 and solution
* Issue 2 and solution
{warning}

||Symptom||Cause||Solution||
|Error message X|Cause description|Solution steps|
|Behavior Y|Another cause|Another solution|

h2. Related Documentation

* [Related Page 1]
* [Related Page 2]
* [External Resource|https://example.com]

----

{note:title=Feedback}
Found an issue with this documentation? Contact [~doc-owner] or create a ticket in [DOCS project|https://jira.example.com/projects/DOCS].
{note}
```

## Example - Filled Template

```
{toc:minLevel=2|maxLevel=3}

----

h2. Overview

This guide explains how to set up and configure the Application Monitoring Service for production environments.

{info:title=Version}
This document applies to version 2.5.0 and later.
Last updated: 2025-01-15
{info}

h2. Prerequisites

Before you begin, ensure you have:

* Docker 20.10+ installed
* Access to the container registry
* Admin credentials for the monitoring dashboard
* Network access to port 9090

h2. Installation

h3. Step 1: Pull the Docker Image

Pull the latest monitoring service image from our registry.

{code:bash}
docker pull registry.example.com/monitoring-service:2.5.0
{code}

h3. Step 2: Create Configuration Directory

Set up the configuration directory structure.

{code:bash}
mkdir -p /opt/monitoring/{config,data,logs}
chmod 755 /opt/monitoring
{code}

h3. Step 3: Deploy the Service

Start the monitoring service container.

{code:bash}
docker run -d \
  --name monitoring-service \
  -p 9090:9090 \
  -v /opt/monitoring/config:/config \
  -v /opt/monitoring/data:/data \
  registry.example.com/monitoring-service:2.5.0
{code}

h2. Configuration

h3. Basic Configuration

||Setting||Description||Default||
|{{retention_days}}|Number of days to retain metrics|{{30}}|
|{{scrape_interval}}|Metrics collection interval|{{15s}}|
|{{log_level}}|Logging verbosity|{{info}}|

{panel:title=Configuration Example|bgColor=#f5f5f5}
{code:yaml}
# /opt/monitoring/config/settings.yaml
retention_days: 90
scrape_interval: 10s
log_level: debug
alerting:
  enabled: true
  slack_webhook: https://hooks.slack.com/...
{code}
{panel}

h3. Advanced Configuration

{expand:Click to see advanced options}
Advanced configuration for high-availability setups:

||Option||Description||
|{{cluster_mode}}|Enable clustering for HA|
|{{replication_factor}}|Number of data replicas|
|{{gossip_port}}|Port for cluster communication|

{code:yaml}
# HA Configuration
cluster_mode: true
replication_factor: 3
gossip_port: 7946
{code}
{expand}

h2. Usage

h3. Basic Usage

Access the monitoring dashboard at {{http://server:9090}} after deployment.

{code:bash}
# Check service status
docker logs monitoring-service

# View current metrics
curl http://localhost:9090/api/v1/status
{code}

h3. Common Use Cases

h4. Use Case 1: Setting Up Alerts

Configure alerting rules in the dashboard under *Settings > Alerts*.

h4. Use Case 2: Creating Custom Dashboards

Navigate to *Dashboards > Create* and use PromQL for custom queries.

h2. Troubleshooting

{warning:title=Common Issues}
If you encounter problems, check the following first:
* Ensure ports 9090 and 7946 are not blocked by firewall
* Verify Docker has sufficient memory (minimum 2GB)
* Check container logs for startup errors
{warning}

||Symptom||Cause||Solution||
|Dashboard not loading|Port blocked|Open port 9090 in firewall|
|High memory usage|Too many metrics|Reduce retention or add memory|
|Cluster not forming|Network issues|Check gossip port connectivity|

h2. Related Documentation

* [Alerting Configuration Guide]
* [Dashboard Best Practices]
* [Prometheus Documentation|https://prometheus.io/docs]

----

{note:title=Feedback}
Found an issue with this documentation? Contact [~ops-team] or create a ticket in [OPS project|https://jira.example.com/projects/OPS].
{note}
```

## Checklist Before Publishing

- [ ] h2. headings for main sections
- [ ] h3. headings for subsections
- [ ] {toc} at the top for navigation
- [ ] {info} panel for version/date information
- [ ] {code:language} blocks for all commands and configuration
- [ ] Tables with ||headers|| for settings and troubleshooting
- [ ] {warning} panel for common issues
- [ ] {expand} for optional/advanced content
- [ ] Links to related documentation
- [ ] Contact information for feedback
