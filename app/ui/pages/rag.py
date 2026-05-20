"""RAG knowledge base management page."""

import httpx
from nicegui import events, ui

from app.i18n.core import _
from app.ui.api_client import api_client, response_error
from app.ui.components.design import empty_state, page_container, page_hero, section_card
from app.ui.layouts.main_layout import main_layout


@ui.page("/rag")
async def rag_page() -> None:
    """Render the RAG knowledge base management page."""
    main_layout()

    with page_container():
        page_hero(
            _("Knowledge Base"),
            _("Manage agronomic documents that ground AI answers and semantic search."),
            icon="travel_explore",
            meta=_("RAG"),
        )

    def notify(notification, message: str, kind: str) -> None:
        notification.set_message(message)
        notification.set_type(kind)
        notification.open()

    # --- Document list ---
    with page_container():
        document_card = section_card(_("Documents"), _("Indexed source material available to the assistant."), icon="description")
    with document_card:
        document_list = ui.column().classes("w-full gap-2 mt-4")

        async def load_documents() -> None:
            """Load documents from the API."""
            document_list.clear()
            with document_list:
                ui.spinner(size="lg")
            try:
                async with api_client() as client:
                    response = await client.get("/api/rag/documents")
                    if response.status_code == 200:
                        documents = response.json()
                        document_list.clear()
                        with document_list:
                            if not documents:
                                empty_state(_("No documents yet"), _("Add agronomic notes, manuals, or documentation to ground AI answers."), icon="note_add")
                            for doc in documents:
                                with ui.row().classes(
                                    "greenhouse-card w-full items-center justify-between p-3 rounded"
                                ):
                                    with ui.column():
                                        ui.label(doc["title"]).classes(
                                            "font-medium"
                                        )
                                        ui.label(
                                            _(
                                                "{source_type} | {count} chars",
                                                source_type=doc.get('source_type', 'N/A'),
                                                count=len(doc.get('content', '')),
                                            )
                                        ).classes("text-xs opacity-60")
                                    ui.badge(
                                        doc.get("source_type", "manual"),
                                        color="blue",
                                    )
            except Exception:
                document_list.clear()
                with document_list:
                    empty_state(_("Failed to load documents"), _("Check API and database availability, then refresh."), icon="sync_problem")

        await load_documents()

        template_notification = ui.notification(position="top", timeout=5)

        async def generate_template_documents() -> None:
            try:
                async with api_client(timeout=120.0) as client:
                    response = await client.post("/api/rag/documents/templates/ukrainian-greenhouse")
                    if response.status_code == 201:
                        created = response.json().get("created", 0)
                        notify(
                            template_notification,
                            _("Generated {created} Ukrainian greenhouse research documents.", created=created),
                            "positive",
                        )
                        await load_documents()
                    else:
                        notify(
                            template_notification,
                            _("Template generation failed: {error}", error=response_error(response)),
                            "negative",
                        )
            except httpx.HTTPError as e:
                notify(template_notification, _("Template generation error: {error}", error=e), "negative")

        with ui.row().classes("gap-2"):
            ui.button(_("Refresh"), on_click=load_documents).props("flat color=primary")
            ui.button(
                _("Generate Ukrainian greenhouse research templates"),
                on_click=generate_template_documents,
            ).props("color=primary icon=auto_awesome")

    # --- Add document form ---
    with page_container():
        add_card = section_card(_("Add Document"), _("Paste, type, or upload knowledge content for indexing."), icon="post_add")
    with add_card:
        title_input = ui.input(label=_("Title")).classes("w-full mt-4")
        source_type_input = ui.select(
            label=_("Source Type"),
            options=["manual", "url", "file", "documentation"],
            value="manual",
        ).classes("w-full")
        content_input = ui.textarea(
            label=_("Content"),
            placeholder=_("Paste or type the agronomic knowledge content here..."),
        ).classes("w-full").props('rows="8"')

        notification = ui.notification(position="top", timeout=5)

        async def load_uploaded_file(event: events.UploadEventArguments) -> None:
            content = event.content.read().decode("utf-8", errors="replace")
            if not title_input.value:
                title_input.set_value(event.name)
            source_type_input.set_value("file")
            content_input.set_value(content)
            notify(notification, _("Loaded file content. Review it, then add the document."), "info")

        ui.upload(
            label=_("Upload text file"),
            auto_upload=True,
            on_upload=load_uploaded_file,
        ).props("accept=.txt,.md,.csv,.json,.log,text/*").classes("w-full")

        async def add_document() -> None:
            """Submit a new document to the knowledge base."""
            if not title_input.value or not content_input.value:
                notify(notification, _("Title and content are required."), "warning")
                return

            try:
                async with api_client() as client:
                    response = await client.post(
                        "/api/rag/documents",
                        json={
                            "title": title_input.value,
                            "source_type": source_type_input.value,
                            "content": content_input.value,
                        },
                    )
                    if response.status_code == 201:
                        notify(notification, _("Document added successfully!"), "positive")
                        title_input.set_value("")
                        content_input.set_value("")
                        await load_documents()
                    else:
                        notify(notification, _("Failed: {error}", error=response_error(response)), "negative")
            except httpx.HTTPError as e:
                notify(notification, _("Error: {error}", error=e), "negative")

        ui.button(_("Add Document"), on_click=add_document).props("color=primary")

    # --- Reindex ---
    with page_container():
        reindex_card = section_card(
            _("Reindex"),
            _("Re-chunk and re-embed all documents. Use after changing the embedding model."),
            icon="sync",
        )
    with reindex_card:

        reindex_notification = ui.notification(position="top", timeout=5)

        async def reindex_all() -> None:
            """Trigger reindexing of all documents."""
            try:
                async with api_client(timeout=120.0) as client:
                    response = await client.post("/api/rag/reindex")
                    if response.status_code == 200:
                        data = response.json()
                        total = len(data.get("results", []))
                        notify(
                            reindex_notification,
                            _("Reindex complete: {total} documents processed.", total=total),
                            "positive",
                        )
                    else:
                        notify(
                            reindex_notification,
                            _("Reindex failed: {error}", error=response_error(response)),
                            "negative",
                        )
            except httpx.HTTPError as e:
                notify(reindex_notification, _("Reindex error: {error}", error=e), "negative")

        ui.button(_("Reindex All Documents"), on_click=reindex_all).props(
            "color=secondary"
        )

    # --- Search ---
    with page_container():
        search_card = section_card(_("Search Knowledge Base"), _("Probe semantic matches before relying on documents in AI answers."), icon="search")
    with search_card:
        search_input = ui.input(
            label=_("Search Query"),
            placeholder=_("e.g. tomato wilting, CO2 optimal levels..."),
        ).classes("w-full")

        search_results = ui.column().classes("w-full gap-2 mt-4")

        async def search_knowledge() -> None:
            """Perform semantic search over the knowledge base."""
            if not search_input.value:
                search_results.clear()
                with search_results:
                    ui.label(_("Enter a search query.")).classes("text-sm opacity-60")
                return

            search_results.clear()
            with search_results:
                ui.spinner(size="lg")

            try:
                async with api_client(timeout=60.0) as client:
                    response = await client.get(
                        "/api/rag/search",
                        params={"query": search_input.value, "limit": 10},
                    )
                    if response.status_code == 200:
                        results = response.json()
                        search_results.clear()
                        with search_results:
                            if not results:
                                empty_state(_("No results found"), _("Try a broader crop, symptom, or environmental query."), icon="search_off")
                            for r in results:
                                with ui.card().classes("greenhouse-card w-full p-3"):
                                    with ui.row().classes(
                                        "w-full items-center justify-between"
                                    ):
                                        ui.label(r["document_title"]).classes(
                                            "font-medium text-sm"
                                        )
                                        ui.label(_("Score: {score:.4f}", score=r['score'])).classes(
                                            "text-xs opacity-60"
                                        )
                                    ui.label(r["content"]).classes(
                                        "text-sm mt-1"
                                    )
                    else:
                        search_results.clear()
                        with search_results:
                            ui.label(_("Search failed: {error}", error=response_error(response))).classes(
                                "text-sm text-red-500"
                            )
            except httpx.HTTPError as e:
                search_results.clear()
                with search_results:
                    ui.label(_("Search error: {error}", error=e)).classes("text-sm text-red-500")

        ui.button(_("Search"), on_click=search_knowledge).props("color=primary")
        ui.space()
        ui.button(
            _("Search on Enter"),
            on_click=search_knowledge
        ).props("flat").bind_enabled_from(search_input, "value")
