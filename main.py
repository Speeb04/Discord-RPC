from pypresence import Presence
import time

var = {}

start = time.time()

with open('setup.txt') as f:
    for x in f:
        try:
            a, b = x.split('=')
            if b == 'none':
                var[a] = None
            else:
                var[a] = b.strip()
        except:
            pass

RPC = Presence(var['client_id'])
RPC.connect()
print('displaying presence')

try:
    while True:
        with open('setup.txt') as f:
            for x in f:
                try:
                    a, b = x.split('=')
                    if b == 'none':
                        var[a] = None
                    else:
                        var[a] = b.strip()
                except:
                    pass
        try:
            RPC.update(state=var['state'], details=var['details'], large_image=var['large image'],
                       small_image=var['small image'], large_text=var['large text'],
                       small_text=var['small text'], start=start,
                       buttons=[{'label': var['button label'], 'url': var['button url']}])
        except:
            RPC.update(state=var['state'], details=var['details'], large_image=var['large image'],
                       small_image=var['small image'], large_text=var['large text'],
                       small_text=var['small text'], start=start)
        time.sleep(15)

except Exception as e:
    print(f"error: {e}")
    while True:
        easteregg = 1
