"""Ratings API (trust-and-disputes plan A4) — a thin adapter over
``fikisha.ratings.services``. The side and the rated subjects are always
resolved server-side from the job."""

from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView
from fikisha.jobs.selectors import get_job
from fikisha.ratings import services
from fikisha.ratings.api.serializers import SubmitRatingSerializer


class JobRatingsView(OrgApiView):
    action_get = "rating.read"
    action_post = "rating.submit"

    def get(self, request: Request, job_id: str) -> Response:
        job = get_job(job_id)
        return Response(services.job_ratings_view(self.actor(request), job))

    def post(self, request: Request, job_id: str) -> Response:
        body = SubmitRatingSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        services.submit(
            actor=self.actor(request),
            job_id=job_id,
            score=body.validated_data["score"],
            comment=body.validated_data.get("comment", ""),
        )
        job = get_job(job_id)
        return Response(
            services.job_ratings_view(self.actor(request), job), status=status.HTTP_201_CREATED
        )
