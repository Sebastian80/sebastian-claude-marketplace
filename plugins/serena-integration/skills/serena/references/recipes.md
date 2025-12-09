# Serena Recipes Reference

Pre-built search recipes for common framework patterns. For quick usage, see SKILL.md.

## Available Recipes

```bash
serena recipe --name list           # Show all available recipes
```

## Oro Commerce Framework

| Recipe | What it finds |
|--------|--------------|
| `oro-payment` | Oro payment classes |
| `oro-checkout` | Oro checkout classes |
| `oro-order` | Oro order classes |
| `oro-entities` | Oro entity classes |
| `oro-controllers` | Oro controllers |

```bash
serena recipe --name oro-payment
serena recipe --name oro-checkout
serena recipe --name oro-order
```

## Third-Party Integrations

| Recipe | What it finds |
|--------|--------------|
| `mollie` | Mollie payment integration |
| `netresearch-payment` | Netresearch payment bundle |

```bash
serena recipe --name mollie
serena recipe --name netresearch-payment
```

## Payment System Recipes

| Recipe | What it finds |
|--------|--------------|
| `payment-methods` | All PaymentMethod classes |
| `payment-providers` | All PaymentProvider classes |
| `payment-factories` | All payment factory classes |

```bash
serena recipe --name payment-methods
serena recipe --name payment-providers
serena recipe --name payment-factories
```

## General Recipes

| Recipe | What it finds |
|--------|--------------|
| `entities` | Entity classes (@ORM\Entity) |
| `controllers` | Controller classes |
| `services` | Service classes |
| `interfaces` | Interface definitions |
| `tests` | Test classes |

```bash
serena recipe --name entities
serena recipe --name controllers
```

## Direct Vendor Search

When recipes don't cover your need, search vendor directly:

```bash
# All vendors
serena find --pattern PaymentMethod --kind class --path vendor/

# Specific vendor
serena find --pattern PaymentMethod --kind class --path vendor/oro
serena find --pattern Mollie --kind class --path vendor/mollie
```

## Performance

Recipes are pre-optimized. Expected times:
- Oro recipes: ~2-3s
- Third-party recipes: ~0.5-1s
- General recipes: ~3-5s

## Creating Custom Recipes

Recipes are defined in `.serena/recipes.yml`. See Serena documentation for syntax.
