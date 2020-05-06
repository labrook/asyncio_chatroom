
# https://www.youtube.com/watch?v=M-UcUs7IMIM

import sys
import asyncio
from itertools import chain


TELNET_EOL = '\r\n'


class Protocol(asyncio.Protocol):
	def __init__(self, chat_room):
		self._chat_room = chat_room
		self._username = None
		self._transport = None
		self._buffer = []

	def connection_made(self, transport):
		self._transport = transport
		self._writeline("Welcome to {}.".format(self._chat_room.name))
		self._writeline("Enter user name: ")

	def data_received(self, raw_data):
		try:
			data = raw_data.decode("utf-8")
		except UnicodeDecodeError as e:
			self._transport._write(str(e).encode("utf-8"))
		else:
			for line in self._accumulated_lines(data):
				self._handle(line)

	def connection_lost(self, exc):
		self._deregister_user()

	def _accumulated_lines(self, data):
		self._buffer.append(data)
		while True:
			tail, newline, head = self._buffer[-1].partition(TELNET_EOL)
			if not newline:
				break
			line = ''.join(chain(self._buffer[:-1], tail))
			self._buffer = [head]
			yield line

	def _handle(self, line):
		if self._username is None:
			self._register_user(line)
		elif line == 'NAMES':
			self._list_users()
		else:
			self._chat_room.message_from(self._username, line)

	def _register_user(self, line):
		username = line.strip()
		if self._chat_room.register_user(username, self._transport):
			self._username = username
		else:
			self._writeline("Username {} not available.".format(username))

	def _deregister_user(self):
		if self._username is not None:
			self._chat_room.deregister_user(self._username)

	def _list_users(self):
		self._writeline("Users here: ")
		for username in self._chat_room.users():
			self._write("  ")
			self._writeline(username)

	def _writeline(self, line):
		self._write(line)
		self._write(TELNET_EOL)

	def _write(self, text):
	 	self._transport.write(text.encode("utf-8"))


class ChatRoom:

	def __init__(self, name, port, loop):
		self._name = name
		self._port = port
		self._loop = loop
		self._username_transport = {}

	@property
	def name(self):
		return self._name

	def run(self):
		coro = self._loop.create_server(
			protocol_factory=lambda: Protocol(self),
			host="",
			port=self._port
			)
		return self._loop.run_until_complete(coro)

	def register_user(self, username, transport):
		if username in self.users():
			return False
		self._username_transport[username] = transport
		self._broadcast("User {} arrived.".format(username))
		print("Username = {}, Transport={}.".format(username, transport))
		print("Event Loop = {}.".format(self._loop))
		return True

	def deregister_user(self, username):
		del self._username_transport[username]
		self._broadcast("User {} departed.".format(username))

	def users(self):
		return self._username_transport.keys()

	def message_from(self, username, message):
		self._broadcast("{}: {}.".format(username, message))

	def _broadcast(self, message):
		for transport in self._username_transport.values():
			transport.write(message.encode("utf-8"))
			transport.write(TELNET_EOL.encode("utf-8"))


def main(argv):
	name = argv[1] if len(argv) >=2 else "Chatterbox"
	port = int(argv[2]) if len(argv) >= 3 else 1234
	loop = asyncio.get_event_loop()
	chat_room = ChatRoom(name, port, loop)
	server = chat_room.run()
	loop.run_forever() 


if __name__ == '__main__':
	main(sys.argv)




