import json

from models import Tool, Function


rates = {
    "USD": 83.33,
    "EUR": 90.91,
    "GBP": 105.26,
    "AED": 22.73,
    "JPY": 0.56,
    "SGD": 61.73,
}

SUPPORTED = ", ".join(rates.keys())

tools = [
    Tool(
        function=Function(
            name="convert_currency",
            description=(
                "Converts between INR and a foreign currency. "
                f"Supported currencies: {SUPPORTED}. "
                "Either from_currency or to_currency must be INR."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The amount to convert",
                    },
                    "from_currency": {
                        "type": "string",
                        "description": "Source currency code (e.g. INR, USD)",
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "Target currency code (e.g. USD, INR)",
                    },
                },
                "required": ["amount", "from_currency", "to_currency"],
            },
        )
    )
]


def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    from_c = from_currency.upper()
    to_c = to_currency.upper()

    if from_c == "INR":
        if to_c not in rates:
            return f"Unsupported currency: {to_c}. Supported: {SUPPORTED}"
        result = amount / rates[to_c]
        return f"{amount:,.2f} INR = {result:,.4f} {to_c} (rate: 1 {to_c} = {rates[to_c]} INR)"

    elif to_c == "INR":
        if from_c not in rates:
            return f"Unsupported currency: {from_c}. Supported: {SUPPORTED}"
        result = amount * rates[from_c]
        return f"{amount:,.2f} {from_c} = {result:,.2f} INR (rate: 1 {from_c} = {rates[from_c]} INR)"

    else:
        return "Either from_currency or to_currency must be INR."


def run_tool(name: str, arguments: str) -> str:
    args = json.loads(arguments)
    if name == "convert_currency":
        return convert_currency(**args)
    return "Unknown tool"
