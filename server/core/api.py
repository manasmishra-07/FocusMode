from rest_framework.views import exception_handler as drf_handler
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError


def ok(data=None, status=200):
    return Response({"success": True, "data": data}, status=status)


def exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is None:
        import logging

        logging.getLogger(__name__).exception("Unhandled API error", exc_info=exc)
        return Response(
            {
                "success": False,
                "error": {
                    "code": "500",
                    "message": "An unexpected error occurred. Please try again.",
                },
            },
            status=500,
        )
    if response is not None:
        details = response.data
        response.data = {
            "success": False,
            "error": {
                "code": str(response.status_code),
                "message": (
                    str(details.get("detail", "Please check your input."))
                    if isinstance(details, dict)
                    else "Request failed"
                ),
                "details": details,
            },
        }
    return response


def paginate(query, request, serializer):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        limit = min(100, max(1, int(request.query_params.get("limit", 20))))
    except ValueError:
        raise ValidationError("Invalid pagination")
    count = query.count()
    return {
        "items": serializer(query[(page - 1) * limit : page * limit], many=True).data,
        "page": page,
        "limit": limit,
        "total": count,
        "totalPages": (count + limit - 1) // limit,
    }
