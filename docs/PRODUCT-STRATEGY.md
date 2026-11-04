# Product boundary

**Repository contract: v3.62.0**

Headron is an MIT-licensed verification foundation for AI-assisted engineering. It provides local verification, contracts, receipts, agent integrations, and a read-only MCP interface. The local core does not require an account.

HeadronOS is a separate workspace and runtime that can consume the public core. Mind API is a separate hosted service intended to provide verification planning to supported clients. Planned capabilities are not evidence that a service or integration is available; consult the [public site](https://headron.tech/) for current product information.

## Data and integration boundary

Public contracts and client integrations should remain usable independently of private services. Local project files, agent credentials, and receipts remain under the user's control. Account identity, subscriptions, and service entitlement belong to their respective hosted services.

A hosted service must describe the data it receives and its handling before customers rely on it. Checkout, key issuance, and entitlement enforcement require end-to-end verification before their behavior can be assumed.

Private product code and operations must not be required to run the public core or its verification. Shared formats and compatibility should be tested across their owning implementations.
