import random
import asyncio
import websockets
import pyaudio
from aioconsole import ainput
import speech_recognition as sr
import concurrent.futures
import functools

executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100


def get_input_device_id():
    p = pyaudio.PyAudio()
    devices = [(i, p.get_device_info_by_index(i)['name'])
               for i in range(p.get_device_count())
               if p.get_device_info_by_index(i).get('maxInputChannels')]

    print('Available devices:')
    for id, name in devices:
        print(f"Device id {id} - {name}")

    return int(input('Please select device id: '))


async def handle_audio(websocket, device_id):
    with sr.Microphone(device_index=device_id, sample_rate=RATE) as source:
        recognizer = sr.Recognizer()
        print('Source sample rate: ', source.SAMPLE_RATE)
        print('Source width: ', source.SAMPLE_WIDTH)
        print('Adjusting for ambient noise...Wait for 2 seconds')
        recognizer.adjust_for_ambient_noise(source, duration=2)
        recognizer.energy_threshold = 1000
        recognizer.dynamic_energy_ratio = 3
        recognizer.dynamic_energy_adjustment_damping = 0.2
        recognizer.pause_threshold = 0.5
        listen_func = functools.partial(
            recognizer.listen, source, phrase_time_limit=30)

        print('Okay, start talking!')
        while True:
            print('\n**Listening...')
            audio = await asyncio.get_event_loop().run_in_executor(executor, listen_func)
            await websocket.send(audio.frame_data)
            print('Sending audio data...')
            await asyncio.sleep(2)


async def handle_text(websocket):
    print('You: ', end="", flush=True)
    while True:
        message = await ainput()
        await websocket.send(message)


async def receive_message(websocket):
    while True:
        message = await websocket.recv()
        if message == '[end]\n':
            print('\nYou: ', end="", flush=True)
        else:
            print(f"{message}", end="", flush=True)


async def start_client(client_id):
    uri = f"ws://localhost:8000/ws/{client_id}"
    mode = input('Select mode (a: audio, t: text): ')
    async with websockets.connect(uri) as websocket:
        if mode.lower() == 'a':
            device_id = get_input_device_id()
            send_task = asyncio.create_task(handle_audio(websocket, device_id))
        else:
            send_task = asyncio.create_task(handle_text(websocket))

        receive_task = asyncio.create_task(receive_message(websocket))

        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            if exc := task.exception():
                print(f"Task raised exception: {exc}")

        for task in pending:
            task.cancel()


async def main():
    client_id = random.randint(0, 1000)
    task = asyncio.create_task(start_client(client_id))
    try:
        await task
    except KeyboardInterrupt:
        task.cancel()
        await asyncio.wait_for(task, timeout=None)
        print("Client stopped by user")


if __name__ == "__main__":
    asyncio.run(main())
