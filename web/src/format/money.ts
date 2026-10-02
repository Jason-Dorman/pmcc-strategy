// Money and prices (UI-SPEC §9): dollars to the cent with a true minus sign; option prices to
// the $0.0001 they're quantized to.
const MINUS = "\u2212";

function signed(value: number, digits: number): string {
  const text = Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return `${value < 0 && Number(text.replace(/,/g, "")) !== 0 ? MINUS : ""}$${text}`;
}

/** `$12,345.67`, `−$1,234.00`. */
export function money(value: number): string {
  return signed(value, 2);
}

/** `$2.3450`: an option price as quantized. */
export function price(value: number): string {
  return signed(value, 4);
}

/** A chart tick: `$15.2k`, `−$850`. */
export function moneyTick(value: number): string {
  if (Math.abs(value) < 1000) return signed(value, 0);
  const text = signed(value / 1000, 1);
  return `${text}k`;
}

/** Money with its sign always shown: `+$803.50`, `−$2,455.00`, `$0.00`. */
export function moneySigned(value: number): string {
  const text = money(value);
  return value > 0 && text !== "$0.00" ? `+${text}` : text;
}
