const INVOICES = new Map<string, Invoice>()

interface Invoice {
  id: string
  userId: string
  total: number
  items: Array<{ id: string; price: number; qty: number }>
  status: string
  chargeId?: string
  refundId?: string
  created: number
}

export async function createInvoice(userId: string, total: number, items: any[]) {
  const id = `inv_${crypto.randomUUID()}`
  const invoice: Invoice = {
    id,
    userId,
    total,
    items,
    status: "pending",
    created: Date.now(),
  }
  INVOICES.set(id, invoice)
  return invoice
}

export async function getInvoice(id: string) {
  return INVOICES.get(id) || null
}

export async function updateInvoice(id: string, updates: Partial<Invoice>) {
  const invoice = INVOICES.get(id)
  if (!invoice) return null
  Object.assign(invoice, updates)
  return invoice
}

export async function listInvoices(userId: string) {
  return [...INVOICES.values()].filter(inv => inv.userId === userId)
}
