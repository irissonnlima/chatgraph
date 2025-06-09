from chatgraph import UserState, ChatID
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

    myUser = UserState(
        chatID=ChatID("5565981027703", "1234567890"),
        menu="state1",
        route="route1",
        protocol="protocol1",
        observation={"obs1": "obs1"},
    )

    myUser.insert()

    myUser = UserState.get_user_state("5565981027703", "1234567890")

    print(myUser)
    myUser.route = "route2"

    myUser.insert()

    myUser.delete()
