from collections import defaultdict
import json
from typing import TYPE_CHECKING

import redis

from ..invocation import DistributedInvocation
from .base_state_backend import InvocationHistory
from .base_state_backend import BaseStateBackend
from ..invocation import DistributedInvocation
from ..util.redis_keys import Key
from .. import exceptions

if TYPE_CHECKING:
    from ..app import Pynenc
    from ..types import Params, Result


class RedisStateBackend(BaseStateBackend):
    def __init__(self, app: "Pynenc") -> None:
        self.client = redis.Redis(host="localhost", port=6379, db=0)
        self.key = Key(app.app_id, "state_backend")
        # self._cache: dict[str, "DistributedInvocation"] = {}
        # self._history: dict[str, list] = defaultdict(list)
        # self._results: dict[str, Any] = {}
        # self._exceptions: dict[str, Exception] = {}
        super().__init__(app)

    def purge(self) -> None:
        self.key.purge(self.client)

    def _upsert_invocation(self, invocation: "DistributedInvocation") -> None:
        self.client.set(
            self.key.invocation(invocation.invocation_id), invocation.to_json()
        )

    def _get_invocation(
        self, invocation_id: str
    ) -> "DistributedInvocation[Params, Result]":
        if inv := self.client.get(self.key.invocation(invocation_id)):
            return DistributedInvocation.from_json(self.app, inv.decode())
        raise KeyError(f"Invocation {invocation_id} not found")

    def _add_history(
        self,
        invocation: "DistributedInvocation",
        invocation_history: "InvocationHistory",
    ) -> None:
        self.client.rpush(
            self.key.history(invocation.invocation_id),
            invocation_history.to_json(),
        )

    def _get_history(
        self, invocation: "DistributedInvocation[Params, Result]"
    ) -> list[InvocationHistory]:
        return [
            InvocationHistory.from_json(h.decode())
            for h in self.client.lrange(
                self.key.history(invocation.invocation_id), 0, -1
            )
        ]

    def _set_result(
        self, invocation: "DistributedInvocation[Params, Result]", result: "Result"
    ) -> None:
        self.client.set(
            self.key.result(invocation.invocation_id),
            self.app.serializer.serialize(result),
        )

    def _get_result(
        self, invocation: "DistributedInvocation[Params, Result]"
    ) -> "Result":
        # return self._results[invocation.invocation_id]
        if res := self.client.get(self.key.result(invocation.invocation_id)):
            return self.app.serializer.deserialize(res.decode())
        raise KeyError(f"Result for invocation {invocation.invocation_id} not found")

    def _set_exception(
        self,
        invocation: "DistributedInvocation[Params, Result]",
        exception: "Exception",
    ) -> None:
        serialized_exception: dict[str, str | bool] = {
            "error_name": exception.__class__.__name__
        }
        if isinstance(exception, exceptions.PynencError):
            serialized_exception["pynenc_error"] = True
            serialized_exception["error_data"] = exception.to_json()
        else:
            serialized_exception["pynenc_error"] = False
            serialized_exception["error_data"] = self.app.serializer.serialize(
                exception
            )
        self.client.set(
            self.key.exception(invocation.invocation_id),
            json.dumps(serialized_exception),
        )

    def _get_exception(
        self, invocation: "DistributedInvocation[Params, Result]"
    ) -> Exception:
        if exc := self.client.get(self.key.exception(invocation.invocation_id)):
            serialized_exception = json.loads(exc.decode())
            if serialized_exception["pynenc_error"]:
                return exceptions.PynencError.from_json(
                    serialized_exception["error_name"],
                    serialized_exception["error_data"],
                )
            return self.app.serializer.deserialize(serialized_exception["error_data"])
        raise KeyError(f"Exception for invocation {invocation.invocation_id} not found")
