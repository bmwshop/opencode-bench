import { getInvoice, updateInvoice } from './billing'

export async function refund(invoiceId: string, reason: string) {
  const invoice = await getInvoice(invoiceId)
  if (!invoice) throw new PaymentError("INVOICE_NOT_FOUND")
  if (invoice.status === "refunded") throw new PaymentError("ALREADY_REFUNDED")

  const result = await stripe.refunds.create({
    charge: invoice.chargeId,
    reason: "requested_by_customer",
    metadata: { invoiceId, reason },
  })

  await updateInvoice(invoiceId, { status: "refunded", refundId: result.id })
  return { refundId: result.id, amount: invoice.total }
}

export async function partialRefund(invoiceId: string, amount: number) {
  const invoice = await getInvoice(invoiceId)
  if (!invoice) throw new PaymentError("INVOICE_NOT_FOUND")
  if (amount > invoice.total) throw new PaymentError("AMOUNT_EXCEEDS_TOTAL")

  const result = await stripe.refunds.create({
    charge: invoice.chargeId,
    amount: Math.round(amount * 100),
  })

  await updateInvoice(invoiceId, { status: "partial_refund", refundId: result.id })
  return { refundId: result.id, amount }
}
