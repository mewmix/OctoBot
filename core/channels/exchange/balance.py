#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

"""
Handles balance changes
"""
from asyncio import CancelledError

from typing import List

from config import CONSUMER_CALLBACK_TYPE, CONFIG_WILDCARD
from core.channels.exchange.exchange_channel import ExchangeChannel
from core.consumer import Consumer
from core.producer import Producer


class BalanceProducer(Producer):
    def __init__(self, channel: ExchangeChannel):
        super().__init__(channel)

    async def receive(self, balance):
        await self.perform(balance)

    async def perform(self, balance):
        try:
            # if personnal_data.portfolio_is_initialized()
            self.channel.exchange_manager.get_personal_data().set_portfolio(balance)  # TODO check if full or just update
            await self.send(balance)
        except CancelledError:
            self.logger.info("Update tasks cancelled.")
        except Exception as e:
            self.logger.error(f"exception when triggering update: {e}")
            self.logger.exception(e)

    async def send(self, balance):
        for consumer in self.channel.get_consumers():
            await consumer.queue.put({
                "balance": balance
            })


class BalanceConsumer(Consumer):
    def __init__(self, callback: CONSUMER_CALLBACK_TYPE):
        super().__init__(callback)

    async def consume(self):
        while not self.should_stop:
            try:
                data = await self.queue.get()
                await self.callback(balance=data["balance"])
            except Exception as e:
                self.logger.exception(f"Exception when calling callback : {e}")


class BalanceChannel(ExchangeChannel):
    def __init__(self, exchange_manager):
        super().__init__(exchange_manager)

    def get_consumers(self) -> List:
        if CONFIG_WILDCARD not in self.consumers:
            self.consumers[CONFIG_WILDCARD] = []

        return self.consumers[CONFIG_WILDCARD]

    def new_consumer(self, callback: CONSUMER_CALLBACK_TYPE, size=0):
        # create dict and list if required
        consumer = BalanceConsumer(callback)
        self.consumers[CONFIG_WILDCARD].append(consumer)
        consumer.run()