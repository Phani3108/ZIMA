"""
POST /api/messages — Teams activity webhook endpoint.

All incoming activity from Teams (messages and Adaptive Card button clicks)
arrives here. The Bot Framework adapter authenticates the request and dispatches
to the ZetaMarketingBot handler.
"""

from fastapi import APIRouter, Request, Response
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from zeta_ima.bot.teams_bot import ZetaMarketingBot
from zeta_ima.config import settings

router = APIRouter()

_adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.microsoft_app_id,
    app_password=settings.microsoft_app_password,
)
_adapter = BotFrameworkAdapter(_adapter_settings)
_bot = ZetaMarketingBot()


async def _on_error(context, error):
    """Log errors and send a friendly fallback message to the user."""
    import traceback
    traceback.print_exc()
    await context.send_activity("Something went wrong. Please try again.")


_adapter.on_turn_error = _on_error


@router.post("/api/messages")
async def messages(req: Request) -> Response:
    """Teams activity webhook — receives all bot traffic."""
    if "application/json" not in req.headers.get("Content-Type", ""):
        return Response(status_code=415)

    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    invoke_response = await _adapter.process_activity(activity, auth_header, _bot.on_turn)
    if invoke_response:
        return Response(
            content=str(invoke_response.body),
            status_code=invoke_response.status,
            media_type="application/json",
        )
    return Response(status_code=201)
