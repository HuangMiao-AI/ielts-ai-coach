# Mobile PWA Notes

IELTS AI Coach exposes a local web-app manifest and install icons through
Streamlit static serving. On a phone connected to the same trusted local
network, open the Streamlit address in Safari or Chrome and choose the
browser's “Add to Home Screen” action.

This release provides an installable shell only. It does not register a
service worker, cache authenticated pages, or claim offline availability.
Closing the browser session can remove unfinished Reading, Writing, Listening,
or Speaking drafts. Submitted Reading and Writing records remain in the local
SQLite database under the authenticated user.

The application must still be served from the trusted computer. Do not expose
the development server directly to the public internet.
