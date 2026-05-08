"""RAG knowledge base management page."""

import httpx
from nicegui import ui

from app.ui.api_client import api_client, response_error
from app.ui.layouts.main_layout import main_layout


@ui.page("/rag")
async def rag_page() -> None:
    """Render the RAG knowledge base management page."""
    main_layout()

    ui.label("Knowledge Base").classes("text-2xl font-bold mt-6")
    ui.label(
        "Manage agronomic knowledge documents for AI-powered search."
    ).classes("text-sm opacity-70 mt-2")

    def notify(notification, message: str, kind: str) -> None:
        notification.set_message(message)
        notification.set_type(kind)
        notification.open()

    # --- Document list ---
    with ui.card().classes("w-full mt-6"):
        ui.label("Documents").classes("text-lg font-bold")

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
                                ui.label("No documents yet.").classes(
                                    "text-sm opacity-60"
                                )
                            for doc in documents:
                                with ui.row().classes(
                                    "w-full items-center justify-between p-2 "
                                    "border border-gray-200 rounded"
                                ):
                                    with ui.column():
                                        ui.label(doc["title"]).classes(
                                            "font-medium"
                                        )
                                        ui.label(
                                            f"{doc.get('source_type', 'N/A')} | "
                                            f"{len(doc.get('content', ''))} chars"
                                        ).classes("text-xs opacity-60")
                                    ui.badge(
                                        doc.get("source_type", "manual"),
                                        color="blue",
                                    )
            except Exception:
                document_list.clear()
                with document_list:
                    ui.label("Failed to load documents.").classes(
                        "text-sm text-red-500"
                    )

        await load_documents()

        ui.button("Refresh", on_click=load_documents).props("flat color=primary")

    # --- Add document form ---
    with ui.card().classes("w-full mt-6"):
        ui.label("Add Document").classes("text-lg font-bold")

        title_input = ui.input(label="Title").classes("w-full")
        source_type_input = ui.select(
            label="Source Type",
            options=["manual", "url", "file", "documentation"],
            value="manual",
        ).classes("w-full")
        content_input = ui.textarea(
            label="Content",
            placeholder="Paste or type the agronomic knowledge content here...",
        ).classes("w-full").props('rows="8"')

        notification = ui.notification(position="top", timeout=5)

        async def add_document() -> None:
            """Submit a new document to the knowledge base."""
            if not title_input.value or not content_input.value:
                notify(notification, "Title and content are required.", "warning")
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
                        notify(notification, "Document added successfully!", "positive")
                        title_input.set_value("")
                        content_input.set_value("")
                        await load_documents()
                    else:
                        notify(notification, f"Failed: {response_error(response)}", "negative")
            except httpx.HTTPError as e:
                notify(notification, f"Error: {e}", "negative")

        ui.button("Add Document", on_click=add_document).props("color=primary")

    # --- Reindex ---
    with ui.card().classes("w-full mt-6"):
        ui.label("Reindex").classes("text-lg font-bold")
        ui.label(
            "Re-chunk and re-embed all documents. Use after changing the embedding model."
        ).classes("text-sm opacity-70 mt-1")

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
                            f"Reindex complete: {total} documents processed.",
                            "positive",
                        )
                    else:
                        notify(
                            reindex_notification,
                            f"Reindex failed: {response_error(response)}",
                            "negative",
                        )
            except httpx.HTTPError as e:
                notify(reindex_notification, f"Reindex error: {e}", "negative")

        ui.button("Reindex All Documents", on_click=reindex_all).props(
            "color=secondary"
        )

    # --- Search ---
    with ui.card().classes("w-full mt-6"):
        ui.label("Search Knowledge Base").classes("text-lg font-bold")

        search_input = ui.input(
            label="Search Query",
            placeholder="e.g. tomato wilting, CO2 optimal levels...",
        ).classes("w-full")

        search_results = ui.column().classes("w-full gap-2 mt-4")

        async def search_knowledge() -> None:
            """Perform semantic search over the knowledge base."""
            if not search_input.value:
                search_results.clear()
                with search_results:
                    ui.label("Enter a search query.").classes("text-sm opacity-60")
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
                                ui.label("No results found.").classes(
                                    "text-sm opacity-60"
                                )
                            for r in results:
                                with ui.card().classes("w-full p-3"):
                                    with ui.row().classes(
                                        "w-full items-center justify-between"
                                    ):
                                        ui.label(r["document_title"]).classes(
                                            "font-medium text-sm"
                                        )
                                        ui.label(f"Score: {r['score']:.4f}").classes(
                                            "text-xs opacity-60"
                                        )
                                    ui.label(r["content"]).classes(
                                        "text-sm mt-1"
                                    )
                    else:
                        search_results.clear()
                        with search_results:
                            ui.label(f"Search failed: {response_error(response)}").classes(
                                "text-sm text-red-500"
                            )
            except httpx.HTTPError as e:
                search_results.clear()
                with search_results:
                    ui.label(f"Search error: {e}").classes("text-sm text-red-500")

        ui.button("Search", on_click=search_knowledge).props("color=primary")
        ui.space()
        ui.button(
            "Search on Enter",
            on_click=search_knowledge
        ).props("flat").bind_enabled_from(search_input, "value")
