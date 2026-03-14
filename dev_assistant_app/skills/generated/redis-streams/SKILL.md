---
name: redis-streams
description: >
  Technical reference for How do I use Redis Streams?. Use when the user asks about this topic.
metadata:
  version: '1.0'
  author: dev-assistant
---

## 1. Executive Summary
Redis Streams model a log data structure, which is typically append-only. They are used for real-time streaming of data chunks, ensuring a smooth user experience by allowing responses to be generated dynamically. Redis Streams provide a powerful, scalable, and fault-tolerant solution for handling real-time data in distributed systems. Unlike Redis Pub/Sub, Streams offer message persistence and more sophisticated consumption patterns, including consumer groups.

## 2. Technical Concepts & Architecture
Redis Streams are an append-only data structure that can be consumed from the beginning, at a random position, or by streaming new messages. The core functionalities revolve around appending records and consuming records. Messages in Redis Streams are persistent. For parallel processing and distributed consumption, Redis Streams support **Consumer Groups**. When a consumer processes a message, it should acknowledge it. If a message is not acknowledged, it remains in the **Pending Entries List (PEL)**, indicating that it has been delivered but not yet processed successfully.

## 3. Implementation & Quick Reference
| Command | Description |
|---------|-------------|
| `XADD key ID field value [field value ...]` | Appends a new entry to a stream. `ID` can be `*` for auto-generation. |
| `XREAD [COUNT count] [BLOCK milliseconds] STREAMS key [key ...] ID [ID ...]` | Reads entries from one or multiple streams. |
| `XGROUP CREATE key groupname ID` | Creates a new consumer group for a stream. `ID` is the last delivered ID. |
| `XREADGROUP GROUP groupname consumername [COUNT count] [BLOCK milliseconds] STREAMS key [key ...] ID [ID ...]` | Reads entries from a stream as part of a consumer group. |
| `XACK key groupname ID [ID ...]` | Acknowledges the successful processing of one or more messages by a consumer group. |
| `XPENDING key groupname` | Shows pending messages for a consumer group. |

**Monitoring:**
Redis Insight can be used to monitor Redis streams, visualize the stream, and inspect messages in real-time.

**Spring Data Redis Example (Consumption):**
```java
ReactiveRedisConnectionFactory connectionFactory = ...
StreamReceiverOptions<String, MapRecord<String, String, String>> options = StreamReceiverOptions.builder()
    .pollTimeout(Duration.ofMillis(100))
    .build();
StreamReceiver<String, MapRecord<String, String, String>> receiver = StreamReceiver.create(connectionFactory, options);
Flux<MapRecord<String, String, String>> messages = receiver.receive(StreamOffset.fromStart("my-stream"));
```

## 4. Practical Examples

**Example 1: Appending a message to a stream**
```redis
XADD mystream * sensor_id 1234 temperature 25.5
XADD mystream * sensor_id 5678 temperature 24.9 humidity 60
```

**Example 2: Creating a consumer group and reading messages**
```redis
# Create a consumer group named 'mygroup' starting from the beginning of 'mystream'
XGROUP CREATE mystream mygroup 0-0 MKSTREAM

# Read messages as consumer 'consumer1' from 'mygroup'
XREADGROUP GROUP mygroup consumer1 COUNT 1 STREAMS mystream >
```

**Example 3: Acknowledging a processed message**
```redis
# After processing a message with ID 1678881773000-0
XACK mystream mygroup 1678881773000-0
```

## 5. Performance & Best Practices
1.  **Use Consumer Groups for Parallel Processing:** Consumer groups allow multiple consumers to process messages from a stream in parallel, distributing the workload and improving throughput.
2.  **Acknowledge Messages Promptly:** It is crucial to acknowledge messages (`XACK`) immediately after successful processing. This removes the message from the Pending Entries List (PEL), preventing it from being reprocessed by the same or another consumer in the group.
3.  **Monitor PEL:** Regularly monitor the Pending Entries List to identify consumers that might be failing to process or acknowledge messages.

## 6. Diagnosis & Troubleshooting
**Problem:** Messages are being reprocessed or remain in the Pending Entries List (PEL) indefinitely.
**Cause:** This typically occurs when a consumer fails to acknowledge a message using `XACK` after processing it. If the acknowledgment is delayed or forgotten, the message will stay in the PEL, and Redis might reassign it to the same consumer or another consumer in the group, leading to inefficiencies and potential data inconsistencies.
**Solution:** Ensure that every message successfully processed by a consumer is promptly acknowledged with the `XACK` command. Implement robust error handling in your consumer logic to ensure acknowledgments are sent even if there are issues during message processing. Regularly inspect the PEL using `XPENDING` to identify and address stuck messages.
