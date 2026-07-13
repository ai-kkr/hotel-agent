import fastapi
import mailtrap as mt
import mailtrap.api.resources.inboxes

from infrastructure.logging import configure_logging

mail = mt.Mail(
    sender=mt.Address(email="someid@demomailtrap.co", name="Mailtrap Test"),
    to=[mt.Address(email="andvikt@gmail.com")],
    subject="You are awesome!",
    text="Congrats for sending test email with Mailtrap!",
    category="Integration Test",
)


# client = mt.MailtrapClient(token=os.environ.get("MAILTRAP_API_KEY", ""))

# response = client.send(mail)
# client.in
# print(response)


app = fastapi.FastAPI()
configure_logging()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
