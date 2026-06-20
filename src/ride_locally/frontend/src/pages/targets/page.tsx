import { NavLink } from "react-router-dom";
import Background from "../../components/Background/Background";
import Layout from "../../components/Layout/Layout";
import { CirclePlus } from "lucide-react";
import TargetList from "../../components/TargetList/TargetList";

export default function Targets(): React.ReactElement {

  return (
    <Layout>
      <Background />
      <div className="panel">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-semibold tracking-tight text-white">
            All targets
          </h1>
          <NavLink
            to="/targets/add"
            title="Add new target"
            className="btn-secondary"
          >
            <CirclePlus size={18} />
            Add new target
          </NavLink>
        </div>
        <hr className="my-6 border-t border-accent-light/40" />
        <TargetList />
      </div>
    </Layout>
  );
}
