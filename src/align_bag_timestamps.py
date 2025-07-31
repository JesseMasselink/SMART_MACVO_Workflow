import argparse
from rosbag2_py import SequentialReader, SequentialWriter, StorageOptions, ConverterOptions
from rosbag2_py import TopicMetadata
from rclpy.serialization import deserialize_message, serialize_message
from rosidl_runtime_py.utilities import get_message
from rclpy.time import Time


def compute_topic_offsets(reader, ref_topic, shift_topics):
    ref_time = None
    shift_times = {topic: None for topic in shift_topics}

    #look for each shift topic an save
    while reader.has_next():
        topic, data, t = reader.read_next()
        if topic == ref_topic and ref_time is None:
            ref_time = t
        elif topic in shift_times and shift_times[topic] is None:
            shift_times[topic] = t
        # Break when all topic shifts are found
        if ref_time is not None and all(v is not None for v in shift_times.values()):
            break
    
    # Safety
    if ref_time is None:
        raise RuntimeError(f"No messages found for reference topic {ref_topic}")

    offsets = {}
    for topic, shift_time in shift_times.items():
        if shift_time is None:
            raise RuntimeError(f"No messages found for shift topic {topic}")
        offsets[topic] = ref_time - shift_time

    return offsets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-bag", required=True)
    parser.add_argument("--output-bag", required=True)
    parser.add_argument("--ref-topic", required=True)
    parser.add_argument("--shift-topics", nargs="+", required=True)
    args = parser.parse_args()

    # Setup reader
    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=args.input_bag, storage_id='sqlite3'),
        ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr')
    )
    # Get topic types from bag file
    topic_types = {t.name: t.type for t in reader.get_all_topics_and_types()}

    # Compute offsets
    # offsets = compute_topic_offsets(reader, args.ref_topic, args.shift_topics)
    # print("Computed offsets (ns):", offsets)

    # Re-open reader to start from the beginning
    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=args.input_bag, storage_id='sqlite3'),
        ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr')
    )

    # Setup writer
    writer = SequentialWriter()
    writer.open(
        StorageOptions(uri=args.output_bag, storage_id='sqlite3'),
        ConverterOptions(input_serialization_format='cdr', output_serialization_format='cdr')
    )

    # Register all topics before writing
    for topic_info in reader.get_all_topics_and_types():
        writer.create_topic(topic_info)

    # Process and write messages
    while reader.has_next():
        topic, data, t = reader.read_next()
        msg_type_str = topic_types[topic]
        msg_type = get_message(msg_type_str)
        msg = deserialize_message(data, msg_type)

        # if topic in offsets:
        #     t += offsets[topic]
        if hasattr(msg, 'header') and hasattr(msg.header, 'stamp'):
                msg.header.stamp = Time(nanoseconds=t).to_msg()

        writer.write(topic, serialize_message(msg), t)


if __name__ == "__main__":
    main()
