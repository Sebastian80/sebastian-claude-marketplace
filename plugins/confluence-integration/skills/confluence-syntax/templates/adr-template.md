# Architecture Decision Record (ADR) Template

Use this template when documenting architecture decisions in Confluence with proper wiki markup syntax.

## Template

```
h2. ADR-[NUMBER]: [Decision Title]

||Field||Value||
|*Status*|{status:colour=Yellow|title=PROPOSED} / {status:colour=Green|title=ACCEPTED} / {status:colour=Red|title=DEPRECATED} / {status:colour=Grey|title=SUPERSEDED}|
|*Date*|YYYY-MM-DD|
|*Decision Makers*|[~person1], [~person2]|
|*Consulted*|[~person3], [~person4]|
|*Informed*|Team / Stakeholders|

h3. Context

[Describe the issue motivating this decision. What is the problem we're trying to solve? What constraints exist?]

{panel:title=Problem Statement|bgColor=#FFEBE9}
[Clear, concise statement of the problem]
{panel}

h3. Decision

[Describe the decision that was made. Be specific and unambiguous.]

{panel:title=Decision Statement|bgColor=#E3FCEF}
We will [decision statement].
{panel}

h3. Consequences

h4. Positive Consequences

* Benefit 1
* Benefit 2
* Benefit 3

h4. Negative Consequences

* Tradeoff 1
* Tradeoff 2

h4. Risks

||Risk||Likelihood||Impact||Mitigation||
|Risk description|Low/Medium/High|Low/Medium/High|Mitigation strategy|

h3. Alternatives Considered

h4. Alternative 1: [Title]

[Description of alternative]

*Pros:*
* Pro 1
* Pro 2

*Cons:*
* Con 1
* Con 2

*Why rejected:* [Reason]

h4. Alternative 2: [Title]

[Description of alternative]

*Pros:*
* Pro 1

*Cons:*
* Con 1
* Con 2

*Why rejected:* [Reason]

h3. Technical Details

{expand:Implementation Notes}
[Technical implementation details, diagrams, code samples]

{code:language}
// Example code or configuration
{code}
{expand}

h3. Related Decisions

* Supersedes: [ADR-XXX: Previous Decision] (if applicable)
* Related to: [ADR-YYY: Related Decision]
* Influenced by: [ADR-ZZZ: Influencing Decision]

h3. References

* [External Documentation|https://example.com]
* [Internal Design Doc]
* [RFC or Proposal]

----

h3. Revision History

||Date||Author||Change||
|YYYY-MM-DD|[~author]|Initial proposal|
|YYYY-MM-DD|[~reviewer]|Updated based on review feedback|
```

## Example - Filled Template

```
h2. ADR-042: Use PostgreSQL for Production Database

||Field||Value||
|*Status*|{status:colour=Green|title=ACCEPTED}|
|*Date*|2025-01-10|
|*Decision Makers*|[~tech.lead], [~architect]|
|*Consulted*|[~dba], [~security.lead], [~ops.lead]|
|*Informed*|Engineering Team, Product Team|

h3. Context

Our application currently uses SQLite for development and testing, but we need a production-ready database solution that can handle our expected scale of 100,000 daily active users and provide enterprise-grade reliability.

{panel:title=Problem Statement|bgColor=#FFEBE9}
We need to select a production database that provides ACID compliance, horizontal read scaling, strong ecosystem support, and meets our security and compliance requirements (SOC2, GDPR).
{panel}

Key constraints:
* Must support ACID transactions
* Must handle 10,000+ concurrent connections
* Must provide point-in-time recovery
* Must be compatible with our Python/Django stack
* Budget: $50,000/year for database infrastructure

h3. Decision

{panel:title=Decision Statement|bgColor=#E3FCEF}
We will use *PostgreSQL 15* as our primary production database, deployed on AWS RDS with Multi-AZ configuration for high availability.
{panel}

Specifically:
* PostgreSQL 15 on AWS RDS
* db.r6g.xlarge instance (4 vCPU, 32 GB RAM)
* Multi-AZ deployment for failover
* Read replicas in 2 additional regions
* Automated daily backups with 30-day retention

h3. Consequences

h4. Positive Consequences

* Industry-proven reliability and ACID compliance
* Excellent Django/SQLAlchemy integration via psycopg2
* Strong JSON support for semi-structured data
* Active community and extensive documentation
* Cost-effective compared to commercial alternatives
* Native support for full-text search reduces need for Elasticsearch

h4. Negative Consequences

* Team needs PostgreSQL-specific training (currently MySQL experienced)
* Migration effort required for existing MySQL development databases
* Some MySQL-specific syntax in codebase needs updating

h4. Risks

||Risk||Likelihood||Impact||Mitigation||
|Performance issues at scale|Low|High|Load testing before launch; read replicas ready|
|Team skill gap|Medium|Medium|Training sessions; pair programming; documentation|
|Migration data loss|Low|Critical|Staged migration; parallel running; extensive testing|

h3. Alternatives Considered

h4. Alternative 1: MySQL 8.0

Standard relational database, team has existing experience.

*Pros:*
* Team already familiar with MySQL
* No migration needed for dev databases
* Lower learning curve

*Cons:*
* Weaker JSON support compared to PostgreSQL
* Less robust full-text search
* Licensing concerns (Oracle ownership)

*Why rejected:* PostgreSQL's superior JSON handling and full-text search capabilities outweigh the migration cost, especially given our semi-structured data requirements.

h4. Alternative 2: Amazon Aurora

AWS-native MySQL/PostgreSQL compatible database.

*Pros:*
* Fully managed with automatic scaling
* Compatible with PostgreSQL
* Excellent AWS integration

*Cons:*
* 20% higher cost than standard RDS PostgreSQL
* Vendor lock-in concerns
* Less control over configuration

*Why rejected:* The additional cost doesn't justify the benefits for our current scale. We can migrate to Aurora later if needed.

h4. Alternative 3: MongoDB

Document database for flexibility.

*Pros:*
* Flexible schema for rapid development
* Native JSON storage
* Horizontal scaling built-in

*Cons:*
* No ACID transactions across documents (until recently)
* Different paradigm requires significant code changes
* Django ORM doesn't natively support MongoDB

*Why rejected:* Our data model is inherently relational; document database would require significant architectural changes and lose ORM benefits.

h3. Technical Details

{expand:Implementation Notes}

h4. Connection Configuration

{code:python}
# Django settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'production_db',
        'USER': 'app_user',
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': 'prod-db.cluster-xxxxx.us-east-1.rds.amazonaws.com',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
{code}

h4. Diagram

!architecture-diagram.png|width=600!

h4. Migration Plan

# Set up RDS PostgreSQL instance (Week 1)
# Configure replication and backups (Week 1)
# Migrate schema using Django migrations (Week 2)
# Data migration using pgloader (Week 2-3)
# Parallel running and testing (Week 3-4)
# Cutover during maintenance window (Week 4)

{expand}

h3. Related Decisions

* Related to: [ADR-038: Cloud Provider Selection (AWS)]
* Related to: [ADR-041: Caching Strategy (Redis)]
* Influences: [ADR-043: Read Replica Strategy] (pending)

h3. References

* [PostgreSQL 15 Documentation|https://www.postgresql.org/docs/15/]
* [AWS RDS for PostgreSQL|https://aws.amazon.com/rds/postgresql/]
* [Django PostgreSQL Notes|https://docs.djangoproject.com/en/4.2/ref/databases/#postgresql-notes]
* [Internal: Database Comparison Analysis]

----

h3. Revision History

||Date||Author||Change||
|2025-01-08|[~architect]|Initial proposal|
|2025-01-09|[~dba]|Added risk assessment and migration plan|
|2025-01-10|[~tech.lead]|Accepted after team review|
```

## Checklist Before Publishing

- [ ] ADR number and descriptive title
- [ ] Status macro (PROPOSED/ACCEPTED/DEPRECATED/SUPERSEDED)
- [ ] Date and decision makers identified
- [ ] Clear context and problem statement in {panel}
- [ ] Unambiguous decision statement in {panel}
- [ ] Positive and negative consequences listed
- [ ] Risk table with likelihood, impact, mitigation
- [ ] At least 2-3 alternatives with pros/cons and rejection reasons
- [ ] Technical details in {expand} section
- [ ] Related decisions linked
- [ ] References to supporting documentation
- [ ] Revision history maintained
