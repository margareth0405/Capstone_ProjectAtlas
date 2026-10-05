# ATLAS responsive and OOP architecture

This guide documents how ATLAS adapts to different devices and where each
application responsibility lives. Code comments should explain intent,
security boundaries, unusual constraints, or interaction between components.
They should not repeat self-explanatory syntax line by line, because redundant
comments become inaccurate when code changes.

## Device layout contract

The final responsive layer is
`library/static/library/css/theme/responsive.css`. It loads after the base,
integration, role, and dark-mode styles so one set of safeguards covers every
page and role.

| Device tier | Viewport | Layout behavior |
| --- | --- | --- |
| Desktop PC | Wider than 1280 px | Persistent resizable sidebar, wide grids, fluid gutters |
| Laptop | 821-1280 px | Persistent sidebar, compact gutters, reduced staff grids |
| Tablet | 601-820 px | Off-canvas navigation drawer, touch targets, fluid content |
| Phone | Up to 600 px | Single-column forms/actions, full-width controls, scrollable tables |
| Narrow phone | Up to 380 px | Optional labels collapse before content can clip |
| Short landscape device | Up to 900 px wide and 520 px high | Compact scrollable navigation and display controls |

All media, form controls, headings, counters, cards, and long identifiers are
contained by their parent. Tables retain their useful column structure inside
keyboard- and touch-scrollable regions instead of shrinking text until it is
unreadable. Safe-area insets protect controls on devices with display cutouts.
Inputs use at least 16 px text on phones and coarse-pointer devices so mobile
browsers do not unexpectedly zoom the page.

The JavaScript sidebar threshold is `sidebarMobileBreakpoint = 820`, matching
the CSS drawer breakpoint. Changing one requires changing the other and the
responsive contract tests.

## Object-oriented responsibility map

ATLAS follows Django's object-oriented request flow:

- `library/views/`: class-based HTTP controllers. Views coordinate a request
  and delegate business work rather than embedding it in templates.
- `library/views/mixins.py`: reusable authorization and page-context behavior.
  Staff, superuser, teacher-resource, and reader permissions remain separate.
- `library/forms.py`: form objects own input normalization and validation.
- `library/services/`: service objects own catalog queries, activity recording,
  analytics, storage, document extraction, AI detection, and deployment checks.
- `library/models.py`: model objects define persisted data and data-level
  invariants.
- `library/context_processors.py` and `library/services/context.py`: shared
  presentation context used by the responsive base templates.
- `library/static/library/js/app.js`: small UI controllers enhance accessible
  server-rendered behavior. The site still works through ordinary links and
  forms without JavaScript.
- `templates/library/base.html`: global metadata, accessibility controls,
  loader, confirmation dialog, footer, and cookie controls.
- `templates/library/dashboard_base.html`: shared role-aware application shell,
  navigation drawer, account menu, breadcrumb, and page-content slot.

Inheritance is used where behavior is genuinely shared. For example,
`StaffPortalBaseView` builds staff context for focused child pages,
`StaffFormView` owns the common validated form workflow, and permission mixins
enforce least privilege before a view executes. Composition is preferred for
business services so they remain replaceable and independently testable.

## Commenting standard

- Every Python module should begin with a short module docstring when its name
  does not fully communicate its role.
- Public classes should document their responsibility and permission boundary.
- Complex algorithms, security decisions, and cross-file breakpoint contracts
  receive comments explaining *why* they exist.
- Shared templates use section comments for global components rather than a
  comment on every HTML element.
- Stylesheets use component and device-tier headings. Individual declarations
  are commented only when the reason is not evident.
- Tests describe behavioral contracts in their method names and docstrings.

This standard keeps the system understandable without filling it with comments
that simply restate the code.

## Verification checklist

For a responsive change:

1. Run `python manage.py test library.tests --keepdb` with the documented local
   test settings.
2. Check the landing, authentication, catalog, resource detail, bookmarks,
   teacher tools, and administrator pages at representative widths: 1440,
   1280, 1024, 820, 768, 600, 390, and 320 px.
3. Repeat a phone check in landscape orientation and with Large text enabled.
4. Confirm keyboard access to the sidebar, account menu, scroll regions,
   dialogs, and forms.
5. Run `python manage.py collectstatic --noinput --clear` after static changes.
