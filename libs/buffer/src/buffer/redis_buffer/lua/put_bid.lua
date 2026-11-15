-- KEYS[1] = слоты буфера
-- KEYS[2] = глобальный счётчик id
-- ARGV[1] = buffer_capacity
-- ARGV[2] = source_type ("production" | "staging" | "test")
-- ARGV[3] = payload (JSON заявки строкой, seq уже внутри)
-- Возврат: { accepted (1/0), slot (-1 при отказе), bid_id }

local PRIO = { production = 1, staging = 2, test = 3 }

local capacity = tonumber(ARGV[1])
local prio     = PRIO[ARGV[2]]
if prio == nil then
  return redis.error_reply('unknown source_type: ' .. ARGV[2])
end

local id = redis.call('INCR', KEYS[2])  -- выдаётся всегда, даже при отказе

-- Д1ОЗ3: первое свободное место от начала, без сдвига
local slot = -1
for i = 1, capacity do
  if redis.call('HEXISTS', KEYS[1], i) == 0 then
    slot = i
    break
  end
end

if slot == -1 then
  -- Д1ОО5: отказ новой заявке, буфер не меняется
  return { 0, -1, id }
end

redis.call('HSET', KEYS[1], slot,
  cjson.encode({ id = id, prio = prio, payload = ARGV[3] }))
redis.call('PUBLISH', 'buffer_updated', tostring(slot))

return { 1, slot, id }