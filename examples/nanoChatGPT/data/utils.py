from torch.utils.data import DataLoader


def create_infinite_dataloader(data, config, collate_fn):
    """
    Creates a dataloader and yields batches from it indefinitely, so that we can request
    batches whenever we like with next.
    """
    dl = DataLoader(
        data,
        batch_size=config["batch_size"],
        shuffle=True,  # TODO: perhaps validation set shouldn't be shuffled?
        collate_fn=collate_fn,
        drop_last=True,
    )
    while True:
        yield from dl