import httpx

webhuk = "https://discord.com/api/webhooks/1465999271705837714/IR_T61EEnaj0Me4nj04AJhnM4UvQ_nORc8dK7cAXh1aVoc_Az_UDCiy3fPmp-01VO7IX"

payload = {
    "content" : 'ratt'
}

httpx.post(webhuk, json=payload)
print("posted")