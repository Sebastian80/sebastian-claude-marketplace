# Confluence Meeting Notes Template

Use this template when creating meeting notes in Confluence with proper wiki markup syntax.

## Template

```
h2. [Meeting Title] - YYYY-MM-DD

{status:colour=Blue|title=SCHEDULED} or {status:colour=Green|title=COMPLETED}

||Detail||Value||
|*Date*|YYYY-MM-DD|
|*Time*|HH:MM - HH:MM (Timezone)|
|*Location*|Room / Video Link|
|*Facilitator*|[~facilitator]|
|*Note Taker*|[~notetaker]|

h3. Attendees

*Present:*
* [~person1] - Role
* [~person2] - Role
* [~person3] - Role

*Absent:*
* [~person4] - Role (excused)

h3. Agenda

# Topic 1 - Owner - Time allocation
# Topic 2 - Owner - Time allocation
# Topic 3 - Owner - Time allocation

h3. Discussion

h4. Topic 1: [Topic Title]

*Presenter:* [~presenter]

Key points discussed:
* Point 1
* Point 2
* Point 3

{panel:title=Decision|bgColor=#E3FCEF}
[Record any decisions made]
{panel}

h4. Topic 2: [Topic Title]

*Presenter:* [~presenter]

Key points discussed:
* Point 1
* Point 2

{note}
[Any notes or concerns raised]
{note}

h3. Decisions

||#||Decision||Owner||Status||
|1|Decision description|[~owner]|{status:colour=Green|title=APPROVED}|
|2|Another decision|[~owner]|{status:colour=Yellow|title=PENDING}|

h3. Action Items

||#||Action||Owner||Due Date||Status||
|1|Action description|[~owner]|YYYY-MM-DD|{status:colour=Yellow|title=TODO}|
|2|Another action|[~owner]|YYYY-MM-DD|{status:colour=Yellow|title=TODO}|

h3. Next Meeting

*Date:* YYYY-MM-DD
*Time:* HH:MM (Timezone)
*Focus:* [Main topic for next meeting]

----

{expand:Meeting Recording/Transcript}
[Link to recording if available]
Duration: XX minutes
{expand}

h3. Related

* Previous meeting: [Previous Meeting Title]
* Related tickets: [PROJ-123], [PROJ-456]
```

## Example - Filled Template

```
h2. Sprint Planning - 2025-01-15

{status:colour=Green|title=COMPLETED}

||Detail||Value||
|*Date*|2025-01-15|
|*Time*|10:00 - 11:30 (CET)|
|*Location*|[Zoom Link|https://zoom.us/j/123456]|
|*Facilitator*|[~scrum.master]|
|*Note Taker*|[~dev.lead]|

h3. Attendees

*Present:*
* [~product.owner] - Product Owner
* [~scrum.master] - Scrum Master
* [~dev.lead] - Development Lead
* [~developer1] - Backend Developer
* [~developer2] - Frontend Developer
* [~qa.lead] - QA Lead

*Absent:*
* [~designer] - UX Designer (on PTO)

h3. Agenda

# Sprint 23 Review - [~scrum.master] - 15 min
# Backlog Refinement - [~product.owner] - 30 min
# Sprint 24 Planning - Team - 45 min

h3. Discussion

h4. Topic 1: Sprint 23 Review

*Presenter:* [~scrum.master]

Key points discussed:
* Completed 34 out of 38 story points (89%)
* 2 stories carried over due to external dependency
* Velocity trending upward over last 3 sprints

{panel:title=Sprint 23 Metrics|bgColor=#f5f5f5}
||Metric||Target||Actual||
|Story Points|38|34|
|Bug Count|<5|3|
|Code Coverage|>80%|84%|
{panel}

h4. Topic 2: Backlog Refinement

*Presenter:* [~product.owner]

Key points discussed:
* Authentication epic ready for development
* Need technical spike for payment integration
* Customer feedback prioritizes mobile improvements

{note}
[~developer1] raised concerns about API rate limits for payment provider. Need to investigate before committing to timeline.
{note}

h4. Topic 3: Sprint 24 Planning

*Presenter:* Team

Stories committed for Sprint 24:
* [PROJ-234] - User authentication flow - 8 pts
* [PROJ-235] - Password reset functionality - 5 pts
* [PROJ-236] - Session management - 5 pts
* [PROJ-240] - Payment spike - 3 pts

{panel:title=Decision|bgColor=#E3FCEF}
Team commits to 21 story points for Sprint 24, reduced from usual 34 due to holiday period.
{panel}

h3. Decisions

||#||Decision||Owner||Status||
|1|Reduce sprint capacity to 21 points|[~scrum.master]|{status:colour=Green|title=APPROVED}|
|2|Prioritize authentication over payments|[~product.owner]|{status:colour=Green|title=APPROVED}|
|3|Schedule technical spike for payments|[~dev.lead]|{status:colour=Green|title=APPROVED}|

h3. Action Items

||#||Action||Owner||Due Date||Status||
|1|Create subtasks for PROJ-234|[~developer1]|2025-01-16|{status:colour=Yellow|title=TODO}|
|2|Research payment provider rate limits|[~developer2]|2025-01-17|{status:colour=Yellow|title=TODO}|
|3|Update sprint board with new stories|[~scrum.master]|2025-01-15|{status:colour=Green|title=DONE}|
|4|Notify stakeholders of reduced capacity|[~product.owner]|2025-01-16|{status:colour=Yellow|title=TODO}|

h3. Next Meeting

*Date:* 2025-01-22
*Time:* 10:00 (CET)
*Focus:* Mid-sprint check-in

----

{expand:Meeting Recording}
[Recording Link|https://zoom.us/rec/123456]
Duration: 87 minutes
{expand}

h3. Related

* Previous meeting: [Sprint 23 Planning - 2025-01-02]
* Sprint board: [Sprint 24 Board|https://jira.example.com/boards/10]
* Related tickets: [PROJ-234], [PROJ-235], [PROJ-236], [PROJ-240]
```

## Checklist Before Publishing

- [ ] Meeting title with date in h2. heading
- [ ] Status macro showing meeting state
- [ ] Attendee list with user mentions [~username]
- [ ] Numbered agenda items
- [ ] Discussion notes per topic with h4. headings
- [ ] {panel} for decisions made
- [ ] Decision table with status macros
- [ ] Action items table with owners and due dates
- [ ] Next meeting details
- [ ] Links to related meetings and tickets
