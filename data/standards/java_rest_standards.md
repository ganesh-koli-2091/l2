# Java REST API Standards — ShopCo Engineering

## HTTP Method Usage
| Operation | Correct Method | Wrong |
|-----------|---------------|-------|
| Read single resource | GET | POST |
| List resources | GET | POST |
| Create resource | POST | GET |
| Full update | PUT | POST |
| Partial update | PATCH | PUT |
| Delete | DELETE | GET/POST |

## Endpoint Naming
- Use lowercase letters and hyphens: `/api/v1/order-items` not `/api/v1/OrderItems`
- Use nouns, not verbs: `/orders` not `/getOrders`
- Use plural nouns for collections: `/orders` not `/order`

## Authentication
- All write endpoints (POST, PUT, PATCH, DELETE) MUST have JWT Bearer authentication
- Read endpoints on sensitive data MUST also authenticate
- Format: `Authorization: Bearer <token>`

## Status Codes
| Scenario | Code |
|----------|------|
| Success GET | 200 |
| Created POST | 201 |
| No content DELETE | 204 |
| Bad input | 400 |
| Not authenticated | 401 |
| Forbidden | 403 |
| Not found | 404 |
| Server error | 500 |

## Request/Response Format
- Always return JSON with `Content-Type: application/json`
- Paginated lists use: `{ "data": [...], "total": N, "page": P, "pageSize": S }`
- Error responses use: `{ "error": "...", "code": "...", "requestId": "..." }`

## Security Checklist
- [ ] No hardcoded credentials in code
- [ ] All SQL queries use parameterized statements
- [ ] Input validation on all user-supplied fields
- [ ] Sensitive fields (passwords, tokens) never logged
- [ ] Rate limiting applied to auth endpoints
