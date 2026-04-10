import { createInvoice } from './billing'

export async function checkout(cart: CartItem[], userId: string) {
  const total = cart.reduce((sum, item) => sum + item.price * item.qty, 0)
  if (total <= 0) throw new PaymentError("EMPTY_CART")

  const invoice = await createInvoice(userId, total, cart)
  const charge = await stripe.charges.create({
    amount: Math.round(total * 100),
    currency: "usd",
    customer: userId,
    metadata: { invoiceId: invoice.id },
  })

  if (charge.status !== "succeeded") {
    throw new PaymentError("CHARGE_FAILED")
  }
  return { invoiceId: invoice.id, chargeId: charge.id, total }
}

interface CartItem {
  id: string
  price: number
  qty: number
}
