# (e) Production Quality E-Commerce Agent (ADK + MCP Toolbox + PostgreSQL)

**Finn**, the shopping assistant of a fictional sports store "GenAI Sports". Customers can
search products, check sizes/stock, manage a shopping list, find the nearest store, pick a
delivery method, place orders, track, change and cancel them.

Based on: [Sports agent codelab – ADK + MCP Toolbox + AlloyDB](https://codelabs.developers.google.com/codelabs/sports-agent-adk-mcp-alloydb?hl=en#8)
and [mtoscano84/sports-agent-adk-mcp-alloydb](https://github.com/mtoscano84/sports-agent-adk-mcp-alloydb).

## Architecture

```
client ──POST /chat (Bearer Google ID token)──> FastAPI server.py
                                                  │ verify token -> user email
                                                  ▼
                                   finn (ADK LlmAgent) + ToolboxToolset
                                   bound_params={"user_email": <verified email>}
                                                  │ HTTP
                                                  ▼
                                   MCP Toolbox for Databases (tools.yaml, 13 SQL tools)
                                                  │ SQL
                                                  ▼
                                   PostgreSQL: users, stores, products, products_variants,
                                   inventory, shopping_lists(_items), delivery_methods,
                                   orders, order_items
```

Tools (`mcp-toolbox/tools.yaml`): `search-products-by-description`, `search-products-by-brand`,
`search-products-by-size`, `get-product-details`, `check-inventory`, `add-product-to-shopping-list`,
`show-shopping-list`, `find-stores-near-user`, `list-delivery-methods`, `place-order`,
`check-order-status`, `update-order-delivery-method`, `cancel-order`.

Production-oriented choices:
- **User identity is never chosen by the LLM.** `user_email` is a *bound parameter* – it is
  removed from the tool schema the model sees and filled in by the backend from the verified
  Google ID token. Every user-scoped SQL statement filters by it, so one customer can't read,
  change or cancel another customer's cart/orders.
- **All data comes from SQL tools** (no hallucinated products/prices); SQL is parameterized
  (`$1, $2`), the model never writes SQL.
- `place-order` is one atomic SQL statement (create order + items + empty cart); write actions
  require user confirmation per the prompt.
- One shared session service (conversation memory across requests), optional database sessions
  via `SESSION_DB_URL`, health endpoint, non-root Docker image, Cloud Run deploy script with a
  private toolbox service (ID-token auth).

## Run locally

```bash
cd 05-ecommerce-agent

docker compose up -d       # PostgreSQL with schema + sample data (db/init.sql)
./run_toolbox.sh           # MCP Toolbox on :5000 (separate terminal)

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && cp .env.example sports_shop_agent/.env     # add GOOGLE_API_KEY

# option A: ADK dev UI (acts as DEMO_USER_EMAIL)
adk web

# option B: the API backend
uvicorn server:app --port 8080
curl -N -X POST localhost:8080/chat -H 'Content-Type: application/json' \
     -d '{"message": "I need running shoes in size 42"}'
# reuse the X-Session-Id response header as "session_id" to continue the conversation
```

Example conversation:
1. `I'm looking for a backpack for a weekend hike`
2. `Tell me more about the Summit Pack 50`
3. `Add it in red to my list` → `Also add Stride Glide 3, size 42, blue`
4. `Show my shopping list` → `Which store is closest to me?`
5. `What delivery options does GenAI Sports Retiro have?`
6. `Place the order with standard home delivery` → agent confirms → order created
7. `Change it to express delivery` → `Show my orders` → `Cancel it`

Sample users: `alex@example.com`, `maria@example.com` (set `DEMO_USER_EMAIL`).

## Deploy (Cloud Run + Cloud SQL)
See `deploy.sh` (Cloud SQL for PostgreSQL, toolbox config as a Secret, private toolbox service,
backend with `GOOGLE_CLIENT_ID` so `/chat` requires a Google ID token).

## Notes / differences from the reference
- **PostgreSQL instead of AlloyDB** so it runs locally for free. Because of that:
  product search uses full-text search instead of `embedding('text-embedding-005', ...)` +
  pgvector, store distance uses the haversine formula on lat/lon instead of PostGIS, and
  the AlloyDB AI natural-language inventory tool is replaced by a normal SQL `check-inventory` tool.
- Sample catalog is small and made-up (fictional brands), not the reference's 1MB dump.
- The reference React frontend is not included; the agent is used through `adk web` or the `/chat` API.
- The reference created a new session service on every request (no memory); here it is shared.
- `update-order-delivery-method` also checks that the order belongs to the signed-in user, and
  `place-order` empties the shopping list after ordering.
- `tools.yaml` uses the MCP Toolbox v1.x flat format.
