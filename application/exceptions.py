class TrxProcessFailed(Exception):
    def __init__(self, message):
        super(TrxProcessFailed, self).__init__('Failed to process bitcoin transaction.\n{msg}'.format(msg=message))


class NotEnoughFunds(Exception):
    def __init__(self):
        super(NotEnoughFunds, self).__init__(
            'User have not enough balance to process transaction'
        )


class WrongApiRequestException(Exception):
    def __init__(self, reason):
        super(WrongApiRequestException, self).__init__(
            'Wrong api request: %s' % reason
        )