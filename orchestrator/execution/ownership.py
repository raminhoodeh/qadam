"""Keep the sole execution lease alive independently of its bounded work."""

from threading import Event, Thread


class ExecutionLeaseKeeper:
    def __init__(self, ledger, lease, *, interval_seconds=30):
        if interval_seconds <= 0:
            raise ValueError("lease_renewal_interval_must_be_positive")
        self.ledger = ledger
        self.lease = lease
        self.interval_seconds = interval_seconds
        self.stopped = Event()
        self.error = None
        self.thread = Thread(target=self._run, name="paper-execution-lease", daemon=True)

    def start(self):
        self.ledger.heartbeat_execution_owner(self.lease)
        self.thread.start()
        return self

    def _run(self):
        while not self.stopped.wait(self.interval_seconds):
            try:
                self.ledger.heartbeat_execution_owner(self.lease)
            except Exception as error:
                # Never reacquire a lost lease or renew a replacement owner's token.
                self.error = error
                self.stopped.set()

    def check(self):
        if self.error is not None:
            from orchestrator.execution.ledger import ExecutionOwnerError
            raise ExecutionOwnerError("execution_owner_renewal_failed") from self.error

    def stop(self):
        self.stopped.set()
        if self.thread.is_alive():
            self.thread.join(timeout=10)
        self.check()
