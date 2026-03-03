# Workflow Templates

## A) Find overlap and propose slots
Input:
- names/calendars
- date + time window
- min duration

Execution checklist:
1. Resolve IDs with priority: mention entity > email lookup > contact search > event organizer fallback.
2. Print/return ID source evidence (how each user_id/open_id was obtained).
3. Resolve calendar_id from IDs.
4. Query busy windows with pagination.

Output:
- 1~3 candidate slots
- busy evidence summary
- ID source evidence summary

## B) Create meeting with attendees
Checklist:
1. Ensure valid user token
2. Create event with `attendees: [{type,user_id}]`
3. Verify attendees via event read + attendees list
4. Return event link and IDs

## C) Cleanup duplicates
1. Filter events by date+title keyword
2. Keep newest confirmed target with correct attendees
3. Delete test/duplicate items
4. Return deleted event_id list
