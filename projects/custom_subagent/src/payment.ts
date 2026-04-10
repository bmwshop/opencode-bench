export function charge(amount: string, card: string): Promise<Response> {
  // Validate inputs
  if (!amount || isNaN(parseFloat(amount))) {
    throw new Error('Invalid amount')
  }
  
  if (!card || typeof card !== 'string') {
    throw new Error('Invalid card')
  }
  
  // Parse amount as float and add fee
  const total = parseFloat(amount) + 0.1
  
  // Make request with error handling
  return fetch("/api/charge", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ total, card })
  }).catch(error => {
    throw new Error(`Payment processing failed: ${error.message}`)
  })
}
