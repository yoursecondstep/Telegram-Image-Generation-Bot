import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from huggingface_hub import InferenceClient
from PIL import Image
import io

# --- Configuration ---
TELEGRAM_BOT_TOKEN = "8316505279:AAEvpH0lEWxRVJJkwUkZ0Qo45T8Dbbtjvt4" # Get this from BotFather
HF_API_TOKEN = "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" # Get this from Hugging Face settings
HF_MODEL_ID = "black-forest-labs/FLUX.1-Kontext-Dev"

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Hugging Face Inference Client ---
hf_client = InferenceClient(model=HF_MODEL_ID, token=HF_API_TOKEN)

# --- Bot Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "Hello! I'm an image editing bot powered by FLUX.1-Kontext-Dev.\n"
        "Send me an image and then send a text prompt to edit it.\n"
        "Example: Send an image, then reply to it with 'make the sky purple'."
    )

# Dictionary to store the last received image for each user
user_images = {}

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming photos and stores them for later processing."""
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file() # Get the highest resolution photo
    photo_bytes = io.BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0) # Reset stream position to the beginning
    user_images[user_id] = photo_bytes # Store the image bytes

    await update.message.reply_text(
        "Image received! Now send me a text prompt to edit it. "
        "You can reply directly to this message with your prompt."
    )
    logger.info(f"Received image from user {user_id}")


async def handle_text_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages, treating them as prompts for image editing."""
    user_id = update.effective_user.id
    prompt = update.message.text

    if user_id not in user_images:
        await update.message.reply_text("Please send an image first, then your editing prompt.")
        return

    image_bytes = user_images[user_id]
    image_bytes.seek(0) # Ensure the stream is at the beginning for the model

    await update.message.reply_text("Processing your image with FLUX.1-Kontext-Dev... This might take a moment.")
    logger.info(f"User {user_id} requested editing with prompt: '{prompt}'")

    try:
        input_image_pil = Image.open(image_bytes)
        # IMPORTANT: Adjust this part based on the actual FLUX.1-Kontext-Dev API
        # As explained in Part 1, check the "Use via API" section on the Space.
        # This is a placeholder call.
        edited_image_pil = hf_client.image_to_image(
            prompt=prompt,
             image=input_image_pil, # Assuming it takes bytes directly from io.BytesIO
            # Add any other required parameters (e.g., negative_prompt, guidance_scale)
        )

        # Convert PIL Image back to bytes for sending via Telegram
        img_byte_arr = io.BytesIO()
        edited_image_pil.save(img_byte_arr, format='PNG') # Or JPEG, depending on quality/size needs
        img_byte_arr.seek(0)

        await update.message.reply_photo(photo=img_byte_arr, caption="Here's your edited image!")
        logger.info(f"Sent edited image to user {user_id}")

        # Clear the image for the user after processing
        del user_images[user_id]

    except Exception as e:
        logger.error(f"Error during image editing for user {user_id}: {e}")
        await update.message.reply_text(
            f"An error occurred while processing your request: {e}\n"
            "Please try again or send a different image/prompt."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update.effective_message:
        await update.effective_message.reply_text(
            'An unexpected error occurred. Please try again later.'
        )


def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))

    # Message handlers
    # Handle photos (any photo)
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    # Handle text messages (any text that is not a command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_prompt))

    # Error handler
    application.add_error_handler(error_handler)

    # Run the bot until you press Ctrl-C
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot stopped.")

if __name__ == "__main__":
    main()


