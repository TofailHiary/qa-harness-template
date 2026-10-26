# Contract diff — a worked example (synthetic)

Everything below is invented to show the method: one operation, three differences, three classes. File paths,
line numbers and values are illustrative.

## The contract, two versions

`openapi/orders.yaml` on the default branch, version 1.3.0 — what every consumer was built against:

```yaml
openapi: 3.0.3
info: { title: Orders API, version: 1.3.0 }
servers:
  - url: https://api.example.com/v1
paths:
  /orders/{id}:
    get:
      parameters:
        - { name: id, in: path, required: true, schema: { type: string, format: uuid } }
      responses:
        "200":
          description: The order
          content:
            application/json:
              schema: { $ref: "#/components/schemas/Order" }
        "404": { description: Not found }
components:
  schemas:
    Order:
      type: object
      required: [id, status, total, created_at]
      additionalProperties: false
      properties:
        id: { type: string, format: uuid }
        status: { type: string, enum: [pending, paid, cancelled] }
        total: { type: number }
        created_at: { type: string, format: date-time }
```

The PR for APP-701 raises the version to 1.4.0 and adds one optional property:

```yaml
        currency: { type: string, description: "ISO 4217 code; omitted on legacy orders" }
```

## The live response on Test, at the PR head (evidence E1)

```http
GET https://api.example.com/v1/orders/7f9c2b1e-0d4a-4c55-9a3e-2b6f1e8d4c10
200 OK
content-type: application/json

{
  "id": "7f9c2b1e-0d4a-4c55-9a3e-2b6f1e8d4c10",
  "status": "paid",
  "total": "49.90",
  "currency": "EUR",
  "created_at": "2026-10-20T08:15:00Z",
  "internal_notes": "customer called twice, refund approved by support"
}
```

## The diff

| # | Element | Contract 1.4.0 says (source) | Live (evidence) | Class | Consumers affected | Result |
|---|---|---|---|---|---|---|
| 1 | `currency` | optional string, new in 1.4.0 (`openapi/orders.yaml:31`) | `"EUR"` (E1) | Additive — documented, optional; old clients ignore unknown fields | web client ignores it (`src/api/orders.ts:12`, E2) | PASS |
| 2 | `total` | `type: number` (`openapi/orders.yaml:27`) | `"49.90"`, a string (E1) | Breaking — type change, in no contract version | web client adds a shipping fee of 5 with `+` and shows `49.905` instead of `54.90` (`src/pages/OrderView.tsx:58`, E3) | FAIL |
| 3 | `internal_notes` | absent; `additionalProperties: false` (`openapi/orders.yaml:22`) | present, staff free text (E1) | Undocumented — and a data-exposure lead | every client; a customer can read staff notes | FAIL |

What the example teaches:

1. **Additive is judged at the consumer.** Row 1 is safe only because the consumer was shown (E2) to ignore
   unknown fields. Had the client validated responses strictly, the same change would be breaking.
2. **Live wrong, contract right → BE.** Row 2: the contract never changed; the serializer did. The consumer row
   is the proof that it matters, not a second bug.
3. **Undocumented is not harmless extra data.** Row 3 is a contract violation and a security lead at once;
   it goes to `security-review` as well as to `bug-verifier`.
4. **Watch the enum too.** If the DB holds a `status` value outside `[pending, paid, cancelled]`
   (`SELECT DISTINCT status`), the API can emit it, and every consumer with an exhaustive `switch` breaks.

## The rows in `run.json`

```json
"register": [
  {"id": "TC-01", "area": "GET /orders/{id} currency", "requirement": "contract 1.4.0", "check": "live 200 body vs schema",
   "result": "PASS", "expected_source": "openapi/orders.yaml:31", "evidence": ["E1", "E2"], "path_exercised": "read", "finding": null},
  {"id": "TC-02", "area": "GET /orders/{id} total", "requirement": "contract 1.4.0", "check": "type of total",
   "result": "FAIL", "expected_source": "openapi/orders.yaml:27", "evidence": ["E1", "E3"], "path_exercised": "read", "finding": "F1"},
  {"id": "TC-03", "area": "GET /orders/{id} extra fields", "requirement": "additionalProperties: false", "check": "fields outside the schema",
   "result": "FAIL", "expected_source": "openapi/orders.yaml:22", "evidence": ["E1"], "path_exercised": "read", "finding": "F2"}
],
"ledger": [
  {"id": "E1", "type": "API request/response", "file": "E1-order-response.json", "env": "TEST",
   "commit": "feature/order-currency @ 3c4d5e6", "captured_at": "2026-10-26T10:12:00Z", "proves": "live body of GET /orders/{id}"},
  {"id": "E2", "type": "Code file reference", "file": "src/api/orders.ts:12", "env": "TEST",
   "commit": "main @ 9a8b7c6", "captured_at": "2026-10-26T10:20:00Z", "proves": "client ignores unknown fields"},
  {"id": "E3", "type": "Code file reference", "file": "src/pages/OrderView.tsx:58", "env": "TEST",
   "commit": "main @ 9a8b7c6", "captured_at": "2026-10-26T10:22:00Z", "proves": "client adds total with +"}
]
```

## GraphQL in one paragraph

The same classes apply. Removing a field or an enum value, or making an argument non-null, is breaking; making
an output field non-null is safe for clients, making it nullable is breaking; a new enum value in an output type
breaks clients that switch exhaustively. Compare the SDL at the baseline and the PR head, then query Test for
records that populate every nullable field.
