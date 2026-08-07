/** Helpers de CNPJ para o Admin (máscara visual; API recebe só dígitos). */

export function cnpjDigits(value: string | null | undefined): string {
  return String(value || "").replace(/\D/g, "").slice(0, 14);
}

/** Formata até 14 dígitos como 00.000.000/0000-00 */
export function formatCnpjMask(value: string | null | undefined): string {
  const d = cnpjDigits(value);
  if (d.length <= 2) return d;
  if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`;
  if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
  if (d.length <= 12) {
    return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
  }
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}
