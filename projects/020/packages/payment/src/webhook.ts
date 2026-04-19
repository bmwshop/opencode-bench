import { updateInvoice } from './billing'

const WEBHOOK_SECRET = process.env.STRIPE_WEBHOOK_SECRET || ''

export async function handleWebhook(req: Request) {
  const sig = req.headers['stripe-signature']
  const event = stripe.webhooks.constructEvent(req.body, sig, WEBHOOK_SECRET)

  switch (event.type) {
    case 'charge.succeeded':
      await onChargeSucceeded(event.data.object)
      break
    case 'charge.failed':
      await onChargeFailed(event.data.object)
      break
    case 'charge.refunded':
      await onChargeRefunded(event.data.object)
      break
    default:
      console.log(`Unhandled event: ${event.type}`)
  }

  return { received: true }
}

async function onChargeSucceeded(charge: any) {
  await updateInvoice(charge.metadata.invoiceId, { status: 'paid', chargeId: charge.id })
}

async function onChargeFailed(charge: any) {
  await updateInvoice(charge.metadata.invoiceId, { status: 'failed' })
}

async function onChargeRefunded(charge: any) {
  await updateInvoice(charge.metadata.invoiceId, { status: 'refunded' })
}
