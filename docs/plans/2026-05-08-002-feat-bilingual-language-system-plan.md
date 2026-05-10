---
title: feat: Bilingual Language System (Ukrainian/English)
type: feat
status: active
date: 2026-05-08
---

# Bilingual Language System (Ukrainian/English)

## Summary

Implement a comprehensive bilingual internationalization (i18n) system for the Smart Greenhouse Fleet Control application, enabling full Ukrainian and English language support across all UI components, pages, labels, and user-facing messages. The system will use Python's built-in gettext with Babel tooling, store user language preferences persistently, and provide a language switcher component for easy language toggling.

---

## Problem Frame

The Smart Greenhouse Fleet Control application currently has all user-facing text hardcoded in English throughout the NiceGUI UI components and pages. Users who prefer Ukrainian language cannot use the application in their native language, limiting accessibility and user experience for Ukrainian-speaking users. As the application evolves, adding new features requires manual attention to language support, leading to inconsistent bilingual coverage and maintenance burden.

---

## Requirements

- R1. **Bilingual Support**: Provide complete Ukrainian and English translations for all user-facing text in the application
- R2. **Language Switcher**: Implement a visible and accessible language switcher UI component (UK/EN toggle)
- R3. **Persistent Language Preference**: Store and retrieve user's selected language across sessions
- R4. **Developer-Friendly Workflow**: Make it easy for developers to add translations for new features
- R5. **Scalable Architecture**: Design the system to easily support additional languages in the future
- R6. **Comprehensive Coverage**: Translate all UI pages, components, labels, buttons, notifications, error messages, and help text

---

## Scope Boundaries

**Included in this implementation:**
- Ukrainian (uk) and English (en) language support
- All NiceGUI pages and components
- User-facing notifications and error messages
- Language persistence using NiceGUI's app.storage.user
- Language switcher component in header
- Developer workflow for adding new translations

**Excluded from this implementation:**
- API response translations (backend error messages remain English)
- Database content translations (stored data remains language-neutral)
- Right-to-left (RTL) language support
- Automatic language detection from browser (manual selection only)
- External documentation translations
- NiceGUI framework's built-in translations (handled by the framework itself)

---

## Context & Research

### Relevant Code and Patterns

**Current UI text patterns:**
- All text is hardcoded in English throughout 17 UI files
- No existing i18n infrastructure or translation system
- Text appears in `ui.label()`, `ui.button()`, `ui.input()` placeholder values, notification messages, and component headers
- Settings infrastructure exists via `ModelSettings` model in PostgreSQL and settings API endpoints

**Key files requiring modification:**
- Layout: `app/ui/layouts/main_layout.py`
- Pages (9 files): dashboard, settings, control, ai_chat, simulator, plants, rag, logs
- Components (6 files): telemetry_cards, alert_panel, chat_message, proposed_action_card, tool_call_trace, telemetry_charts

**State management:**
- Page-level state using dictionaries
- NiceGUI's `app.storage.user` available for persistent client-side storage
- Database-based settings via `ModelSettings` model

### Institutional Learnings

No existing institutional learnings for i18n implementation in this codebase. This is greenfield work.

### External References

- **NiceGUI i18n Discussion #5840**: Official guidance from NiceGUI core team on implementing translations using gettext and Babel
- **Python gettext module**: Built-in internationalization framework
- **Babel documentation**: Message extraction, compilation, and translation workflow tooling
- **FastAPI i18n best practices**: Language detection and middleware patterns

---

## Key Technical Decisions

- **Translation library**: Python's built-in `gettext` with Babel tooling for message extraction and compilation
  - **Rationale**: Zero runtime dependencies, industry-standard .po file format that professional translators use, excellent tooling, scales well to many languages
- **Translation storage**: Standard GNU gettext format with `locales/` directory containing .po (source) and .mo (compiled) files
  - **Rationale**: Compatible with standard translation tools (Poedit, Lokalise, Weblate), version-control friendly, separates translation from code
- **Language persistence**: NiceGUI's `app.storage.user` for client-side preference storage
  - **Rationale**: Survives page reloads, server-side storage compatible with NiceGUI's architecture, no database schema changes needed for MVP
- **Language switcher placement**: Header bar alongside existing branding elements
  - **Rationale**: Visible on all pages, follows common UI patterns, accessible without navigation
- **Default language**: English (en)
  - **Rationale**: Current application is English-only, maintains existing behavior for new users
- **Translation function naming**: Standard `_()` alias following Python i18n conventions
  - **Rationale**: Recognizable to Python developers, minimal code change, IDE-friendly

---

## Open Questions

### Resolved During Planning

- **Q: Should language preference be stored in database or client-side storage?**
  - **A**: Client-side using NiceGUI's `app.storage.user` for MVP. Database storage can be added later if multi-user server-side preferences are needed.

- **Q: Should we extract all existing strings at once or incrementally?**
  - **A**: Extract all strings in one pass using Babel to create the initial translation template, then translate incrementally. This ensures complete coverage.

- **Q: How to handle dynamic strings with variables (e.g., "Greenhouse {id}")?**
  - **A**: Use gettext's string interpolation with named placeholders, which .po files support natively.

### Deferred to Implementation

- **Q: Should the language switcher use flag icons, text labels, or both?**
  - **A**: Implementation decision based on visual design preferences. Flag emojis (🇺🇦/🇺🇸) with text labels is the starting point.

- **Q: Exact placement of language switcher in header layout**
  - **A**: Implementation can adjust based on available space and visual hierarchy.

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

### Translation Flow Architecture

```mermaid
graph TD
    A[User visits page] --> B{Language in storage?}
    B -->|Yes| C[Load stored language]
    B -->|No| D[Use default: English]
    C --> E[Get translation function]
    D --> E
    E --> F[Render page with _() wrapper]
    F --> G[User clicks language switcher]
    G --> H[Set language in app.storage.user]
    H --> I[Reload page]
    I --> C
```

### File Structure

```
smart-greenhouse-ai/
├── locales/
│   ├── uk/
│   │   └── LC_MESSAGES/
│   │       ├── messages.po    # Ukrainian translations (editable)
│   │       └── messages.mo    # Compiled Ukrainian (auto-generated)
│   ├── en/
│   │   └── LC_MESSAGES/
│   │       ├── messages.po    # English translations (editable)
│   │       └── messages.mo    # Compiled English (auto-generated)
│   └── messages.pot           # Translation template (auto-generated)
├── babel.cfg                  # Babel extraction configuration
├── app/
│   ├── i18n/                  # NEW: Internationalization module
│   │   ├── __init__.py
│   │   └── core.py            # Translation functions and language management
│   └── ui/
│       └── components/
│           └── language_switcher.py  # NEW: Language switcher UI component
```

### Translation Wrapper Pattern

```python
# Core translation function (app/i18n/core.py)
def _(message: str) -> str:
    """Get translated string for current language."""
    lang = get_current_language()
    translator = get_translation_function(lang)
    return translator(message)

# Usage in UI code (pattern to apply throughout)
from app.i18n.core import _

ui.label(_('Dashboard'))
ui.button(_('Refresh'), on_click=handler)
```

---

## Implementation Units

- U1. **Create i18n infrastructure module**

**Goal:** Establish the core internationalization system with translation loading and language management.

**Requirements:** R1, R3, R5

**Dependencies:** None

**Files:**
- Create: `app/i18n/__init__.py`
- Create: `app/i18n/core.py`

**Approach:**
- Create translation function loader using Python's gettext module
- Implement `get_current_language()` to read from `app.storage.user`
- Implement `set_language()` to write preference and trigger reload
- Create `_()` convenience wrapper function following Python conventions
- Define supported languages constant (uk, en) and default (en)
- Add graceful fallback to English if translation files are missing

**Patterns to follow:**
- Settings pattern from `app/config.py` for configuration constants
- Repository pattern for clean separation of concerns

**Test scenarios:**
- Happy path: Load Ukrainian translation function successfully
- Happy path: Load English translation function successfully
- Edge case: Missing translation file returns English text
- Edge case: Invalid language code falls back to default
- Integration: Setting language updates storage and persists across page reload

**Verification:**
- Translation function returns correct strings for each language
- Language preference persists after page reload
- Fallback behavior works when translation files are missing

---

- U2. **Create Babel configuration and translation workflow**

**Goal:** Set up the translation file structure and Babel tooling for extracting and compiling translations.

**Requirements:** R4, R5

**Dependencies:** U1

**Files:**
- Create: `babel.cfg`
- Create: `locales/uk/LC_MESSAGES/messages.po`
- Create: `locales/en/LC_MESSAGES/messages.po`
- Create: `locales/messages.pot`

**Approach:**
- Create `babel.cfg` configuration for Python file extraction
- Run `pybabel extract` to generate initial `messages.pot` template from all UI files
- Initialize Ukrainian and English message catalogs using `pybabel init`
- Add Babel to development dependencies in `pyproject.toml`
- Create initial placeholder translations for testing
- Add `.mo` files to `.gitignore` (compiled, auto-generated)
- Keep `.po` and `.pot` files in version control

**Patterns to follow:**
- Dependency management pattern from `pyproject.toml`

**Test scenarios:**
- Happy path: `pybabel extract` generates template with all strings
- Happy path: `pybabel init` creates language-specific catalogs
- Happy path: `pybabel compile` generates .mo files without errors
- Edge case: Extraction handles strings with quotes and special characters
- Edge case: Extraction handles multi-line strings

**Verification:**
- Template file contains all extractable strings from UI files
- Language catalog files are properly formatted and valid
- Compilation generates binary .mo files in correct locations
- Workflow documented in plan for future developers

---

- U3. **Create language switcher UI component**

**Goal:** Build a reusable language switcher component for the header.

**Requirements:** R2

**Dependencies:** U1

**Files:**
- Create: `app/ui/components/language_switcher.py`
- Test: `tests/unit/test_language_switcher.py`

**Approach:**
- Create `language_switcher()` function that renders buttons for UK/EN
- Use flag emojis (🇺🇦/🇺🇸) with language labels for clarity
- Highlight currently active language visually
- Wire click handlers to `set_language()` function
- Trigger page reload after language change to apply translations
- Style to integrate with existing header layout

**Patterns to follow:**
- Component pattern from `app/ui/components/telemetry_cards.py`
- NiceGUI button and row layout patterns

**Test scenarios:**
- Happy path: Clicking Ukrainian button sets language and reloads
- Happy path: Clicking English button sets language and reloads
- Happy path: Active language button is visually distinguished
- Edge case: Multiple rapid clicks only trigger one reload

**Verification:**
- Component renders two language buttons with flags and labels
- Clicking a button changes language preference in storage
- Page reloads after language selection
- Active language is visually indicated

---

- U4. **Integrate language switcher into main layout**

**Goal:** Add the language switcher to the header so it's visible on all pages.

**Requirements:** R2

**Dependencies:** U3

**Files:**
- Modify: `app/ui/layouts/main_layout.py`

**Approach:**
- Import `language_switcher` component
- Add switcher to header row, positioned after branding elements
- Ensure horizontal alignment and spacing with existing header content
- Maintain responsive layout behavior

**Patterns to follow:**
- Existing header layout pattern in `main_layout.py`

**Test scenarios:**
- Happy path: Language switcher appears on all pages
- Happy path: Switcher is positioned correctly in header
- Happy path: Switcher does not break on mobile/narrow viewports
- Integration: Switcher appears alongside existing header elements

**Verification:**
- Language switcher visible in header on dashboard page
- Language switcher visible in header on settings page
- Language switcher visible in header on all other pages
- Header layout remains visually balanced

---

- U5. **Extract and translate main layout strings**

**Goal:** Replace hardcoded strings in main layout with translatable strings and provide Ukrainian translations.

**Requirements:** R1, R6

**Dependencies:** U2

**Files:**
- Modify: `app/ui/layouts/main_layout.py`
- Modify: `locales/uk/LC_MESSAGES/messages.po`
- Modify: `locales/en/LC_MESSAGES/messages.po`

**Approach:**
- Wrap all header and sidebar strings with `_()` function
- Strings include: "Smart Greenhouse Fleet", "Fleet Control System", "Menu", "Operations", "Intelligence", "System", all navigation link text
- Run `pybabel extract` to update template
- Run `pybabel update` to merge into existing catalogs
- Provide Ukrainian translations for all extracted strings
- Compile translations with `pybabel compile`

**Patterns to follow:**
- Translation wrapper pattern established in U1

**Test scenarios:**
- Happy path: All layout strings display in English when language is 'en'
- Happy path: All layout strings display in Ukrainian when language is 'uk'
- Edge case: Missing translation falls back to English
- Integration: Language switcher changes layout text immediately after reload

**Verification:**
- Header displays in selected language
- Sidebar section labels display in selected language
- All navigation links display in selected language
- Language switcher toggle changes all layout text

---

- U6. **Extract and translate dashboard page strings**

**Goal:** Replace hardcoded strings in dashboard page with translatable strings and provide Ukrainian translations.

**Requirements:** R1, R6

**Dependencies:** U2

**Files:**
- Modify: `app/ui/pages/dashboard.py`
- Modify: `locales/uk/LC_MESSAGES/messages.po`
- Modify: `locales/en/LC_MESSAGES/messages.po`

**Approach:**
- Wrap all user-facing strings with `_()` function
- Strings include: page title, section headers, empty state messages, loading messages, error messages, metric labels
- Extract and update translation catalogs
- Provide Ukrainian translations
- Compile and test

**Patterns to follow:**
- Translation wrapper pattern

**Test scenarios:**
- Happy path: Dashboard displays in English when language is 'en'
- Happy path: Dashboard displays in Ukrainian when language is 'uk'
- Edge case: Dynamic strings with variables interpolate correctly
- Edge case: Error messages translate correctly

**Verification:**
- Page title displays in selected language
- Card headers display in selected language
- Empty state messages display in selected language
- Loading and error messages display in selected language

---

- U7. **Extract and translate settings page strings**

**Goal:** Replace hardcoded strings in settings page with translatable strings and provide Ukrainian translations.

**Requirements:** R1, R6

**Dependencies:** U2

**Files:**
- Modify: `app/ui/pages/settings.py`
- Modify: `locales/uk/LC_MESSAGES/messages.po`
- Modify: `locales/en/LC_MESSAGES/messages.po`

**Approach:**
- Wrap all user-facing strings with `_()` function
- Strings include: page title, descriptions, section headers, button labels, status messages, table headers
- Extract and update translation catalogs
- Provide Ukrainian translations
- Compile and test

**Patterns to follow:**
- Translation wrapper pattern

**Test scenarios:**
- Happy path: Settings page displays in English when language is 'en'
- Happy path: Settings page displays in Ukrainian when language is 'uk'
- Edge case: Dynamic status messages with timestamps interpolate correctly

**Verification:**
- Page title and descriptions display in selected language
- Form labels and placeholders display in selected language
- Button labels display in selected language
- Success and error messages display in selected language

---

- U8. **Extract and translate remaining pages**

**Goal:** Replace hardcoded strings in all remaining pages (control, ai_chat, simulator, plants, rag, logs) with translatable strings and provide Ukrainian translations.

**Requirements:** R1, R6

**Dependencies:** U2

**Files:**
- Modify: `app/ui/pages/control.py`
- Modify: `app/ui/pages/ai_chat.py`
- Modify: `app/ui/pages/simulator.py`
- Modify: `app/ui/pages/plants.py`
- Modify: `app/ui/pages/rag.py`
- Modify: `app/ui/pages/logs.py`
- Modify: `locales/uk/LC_MESSAGES/messages.po`
- Modify: `locales/en/LC_MESSAGES/messages.po`

**Approach:**
- Process each page file independently
- Wrap all user-facing strings with `_()` function
- Extract and update translation catalogs after each file
- Provide Ukrainian translations for all strings
- Compile and test each page

**Patterns to follow:**
- Translation wrapper pattern

**Test scenarios:**
- Happy path: Each page displays in English when language is 'en'
- Happy path: Each page displays in Ukrainian when language is 'uk'
- Edge case: Chat messages and dynamic content handle translation correctly
- Integration: Language switcher works consistently across all pages

**Verification:**
- All page titles display in selected language
- All form controls display in selected language
- All status messages display in selected language
- All notifications display in selected language

---

- U9. **Extract and translate UI components**

**Goal:** Replace hardcoded strings in all reusable UI components with translatable strings and provide Ukrainian translations.

**Requirements:** R1, R6

**Dependencies:** U2

**Files:**
- Modify: `app/ui/components/telemetry_cards.py`
- Modify: `app/ui/components/alert_panel.py`
- Modify: `app/ui/components/chat_message.py`
- Modify: `app/ui/components/proposed_action_card.py`
- Modify: `app/ui/components/tool_call_trace.py`
- Modify: `locales/uk/LC_MESSAGES/messages.po`
- Modify: `locales/en/LC_MESSAGES/messages.po`

**Approach:**
- Process each component file independently
- Wrap all user-facing strings with `_()` function
- Pay special attention to metric labels, status badges, and dynamic card content
- Extract and update translation catalogs
- Provide Ukrainian translations
- Compile and test

**Patterns to follow:**
- Translation wrapper pattern

**Test scenarios:**
- Happy path: All components display in English when language is 'en'
- Happy path: All components display in Ukrainian when language is 'uk'
- Edge case: Metric labels with units format correctly in Ukrainian
- Edge case: Status badges translate correctly
- Integration: Components render correctly when used from different pages

**Verification:**
- Telemetry cards display metric labels in selected language
- Alert panel displays all messages in selected language
- Chat messages display headers and labels in selected language
- Proposed action cards display status labels in selected language
- Tool call traces display in selected language

---

- U10. **Create developer documentation for i18n workflow**

**Goal:** Document how developers should add translations for new features and maintain the i18n system.

**Requirements:** R4

**Dependencies:** U2

**Files:**
- Create: `docs/I18N.md`

**Approach:**
- Document the translation workflow: extract → translate → compile
- Provide examples of wrapping strings with `_()`
- Document Babel commands for extracting, updating, and compiling
- Explain file structure and where translation files live
- Provide troubleshooting for common issues
- Include checklist for adding translations to new features

**Patterns to follow:**
- Documentation pattern from existing `docs/*.md` files

**Test scenarios:**
- Happy path: New developer can follow guide to add translations
- Happy path: Guide covers all common workflow scenarios
- Edge case: Guide addresses troubleshooting for missing translations

**Verification:**
- Document exists at specified path
- Document covers extraction workflow
- Document covers translation workflow
- Document covers compilation workflow
- Document provides examples
- Document is accessible and readable

---

## System-Wide Impact

- **Interaction graph:** All NiceGUI pages and components will now depend on the i18n module for text rendering
- **Error propagation:** Translation failures fall back gracefully to English (missing .mo files or missing keys)
- **State lifecycle risks:** Language preference stored in `app.storage.user` persists across sessions but may reset if storage is cleared; this is acceptable behavior
- **API surface parity:** No API changes required; this is UI-only change
- **Integration coverage:** Unit tests for translation function, manual testing for UI rendering across all pages
- **Unchanged invariants:** All existing functionality remains identical; only language of displayed text changes

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Translation completeness may be incomplete at launch | Prioritize high-visibility pages first (dashboard, settings), add placeholder translations for lower-priority areas |
| Ukrainian translation quality may vary | Use professional translation or native speaker review; consider community feedback loop |
| Performance impact of loading translations on every page | Translation loading is cached by gettext; performance impact is negligible |
| Breaking existing UI during refactoring | Test each page individually after translation wrapping; commit incrementally |
| Developer workflow may be unfamiliar | Provide comprehensive documentation; add helper scripts for common operations |

---

## Documentation / Operational Notes

- **New documentation:** Create `docs/I18N.md` covering translation workflow for developers
- **Updated documentation:** Update README.md to mention bilingual support
- **Operational considerations:** None; this is client-side only with no database or infrastructure changes
- **Monitoring considerations:** None for MVP; could add language usage analytics later

---

## Sources & References

- Research agents: ce-repo-research-analyst, ce-best-practices-researcher (executed 2026-05-08)
- NiceGUI i18n Discussion #5840: Official implementation guidance
- Python gettext documentation: Built-in module reference
- Babel documentation: Message extraction and compilation tooling
- Current codebase: app/ui/ directory structure and patterns
